#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
01_transcricao.py — SPIN Analyzer (ASR + Diarização local + Roles robustos)
CPU-only, sem depender de pyannote gated.

Saídas:
- TXT: linhas "[VENDEDOR] ..." / "[CLIENTE] ..."
- JSON: segments + diarize_tag/conf + spk_to_role + speaker_points + debug

Diarização:
- auto: tenta embed_kmeans (SpeechBrain ECAPA embeddings + clustering) -> se falhar, turn_taking -> mono
- pyannote: tenta pyannote se houver token + acesso (pode falhar gated)
- embed_kmeans: forçar diarização local
- turn_taking: fallback por pausas (sem modelo)
- none: mono

Roles:
- Base global por speaker_points: melhor speaker = VENDEDOR, demais = CLIENTE
- Overrides por segmento somente quando forte
- Reparos na abertura (~45s) + smoothing de ilhas (COM TRAVA POR CONFIANÇA)

Portugues:
- força language=pt no faster-whisper
- split_by_punct + VAD agressivo
- dicionário de correções sempre (se existir), sem quebrar se não existir
"""

import os
import re
import json
import argparse
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

# --- PATHS para importar helpers do repo, se existirem ---
sys.path.insert(0, "/root/analyze_service/repo")
sys.path.insert(0, "/root/analyze_service/repo/scripts_base")

# -----------------------------
# Configs (TRAVAS IMPORTANTES)
# -----------------------------

ROLE_SMOOTH_MIN_DIAR_CONF = 0.62   # se diarize_conf >= isso, smoothing NÃO mexe (fora abertura)
ROLE_SMOOTH_MIN_GLOBAL_CONF = 0.62
ROLE_SMOOTH_OPENING_SECS = 45.0
ROLE_SMOOTH_MAX_DUR = 2.5
ROLE_SMOOTH_MAX_WORDS = 7

# -----------------------------
# Utilitários
# -----------------------------

def safe_mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def write_text(p: Path, s: str):
    p.write_text(s, encoding="utf-8")

def write_json(p: Path, obj: Any):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def split_by_punct(text: str) -> List[str]:
    t = norm_ws(text)
    if not t:
        return []
    parts = re.split(r"(?<=[\.\!\?\:;])\s+", t)
    out = [norm_ws(p) for p in parts if norm_ws(p)]
    return out if out else [t]

def is_short_ack(text: str) -> bool:
    t = norm_ws(text).lower()
    if not t:
        return True
    return bool(re.match(r"^(sim|não|nao|ok|certo|perfeito|entendi|beleza|tá|ta|uhum|hum|isso|claro|pois não)\s*[\.!\?]*$", t))

# -----------------------------
# Dicionário de correções
# -----------------------------

DICT_LINE_PATTERNS = [
    re.compile(r"^(.*?)\t(.*?)$"),
    re.compile(r"^(.*?)\s*=>\s*(.*?)$"),
    re.compile(r"^(.*?)\s*->\s*(.*?)$"),
]

def load_replacement_dict(dict_path: Path) -> List[Tuple[str, str]]:
    if not dict_path.exists():
        return []
    rules: List[Tuple[str, str]] = []
    for raw in read_text(dict_path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        a = b = None
        for pat in DICT_LINE_PATTERNS:
            m = pat.match(line)
            if m:
                a = (m.group(1) or "").strip()
                b = (m.group(2) or "").strip()
                break
        if a is None and "=" in line:
            left, right = line.split("=", 1)
            a, b = left.strip(), right.strip()
        if a and b:
            rules.append((a, b))
    return rules

def apply_replacement_dict(text: str, rules: List[Tuple[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
    if not rules:
        return text, []
    original = text
    repairs = []
    out = text

    for src, dst in rules:
        if not src:
            continue
        is_wordish = bool(re.match(r"^[\wÀ-ÿ]+$", src, flags=re.UNICODE))
        if is_wordish:
            pat = re.compile(rf"\b{re.escape(src)}\b", flags=re.IGNORECASE | re.UNICODE)
        else:
            pat = re.compile(re.escape(src), flags=re.IGNORECASE | re.UNICODE)

        new_out, n = pat.subn(dst, out)
        if n > 0:
            repairs.append({"src": src, "dst": dst, "count": str(n)})
            out = new_out

    if out != original:
        out = norm_ws(out)
    return out, repairs

# -----------------------------
# Segmentos
# -----------------------------

@dataclass
class Seg:
    start: float
    end: float
    text: str
    speaker: str = "SPEAKER_00"
    diarize_conf: float = 0.0
    role: str = "UNK"
    role_override: bool = False
    opening_repair: bool = False
    pseudo_speaker: bool = False  # speaker veio de heurística (turn_taking) e não acústico

def seg_duration(s: Seg) -> float:
    return max(0.0, float(s.end) - float(s.start))

def seg_words(s: Seg) -> int:
    return len(re.findall(r"\w+", s.text or "", flags=re.UNICODE))

# -----------------------------
# ASR (faster-whisper)
# -----------------------------

def transcribe_faster_whisper(
    audio_path: Path,
    model_name: str,
    compute_type: str,
    beam_size: int,
    condition_on_previous_text: bool,
    vad_filter: bool,
    vad_parameters: Optional[Dict[str, Any]],
    language: str = "pt",
) -> Tuple[List[Seg], Dict[str, Any]]:
    meta: Dict[str, Any] = {"asr": "faster-whisper", "model": model_name, "compute": compute_type, "beam": beam_size}
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        meta["error"] = f"import faster_whisper failed: {repr(e)}"
        return [], meta

    try:
        model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
    except Exception as e:
        meta["error"] = f"load model failed: {repr(e)}"
        return [], meta

    try:
        segments_iter, info = model.transcribe(
            str(audio_path),
            beam_size=beam_size,
            condition_on_previous_text=condition_on_previous_text,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters or None,
            word_timestamps=False,
            temperature=0.0,
            language=language,  # força PT
        )
        meta["language"] = getattr(info, "language", None)
        meta["language_probability"] = getattr(info, "language_probability", None)
    except Exception as e:
        meta["error"] = f"transcribe failed: {repr(e)}"
        return [], meta

    out: List[Seg] = []
    for s in segments_iter:
        txt = norm_ws(getattr(s, "text", "") or "")
        if not txt:
            continue
        out.append(Seg(start=float(s.start), end=float(s.end), text=txt))
    meta["n_segments"] = len(out)
    return out, meta

def explode_long_segments(segments: List[Seg], do_split_by_punct: bool, max_words: int = 26) -> List[Seg]:
    if not segments or not do_split_by_punct:
        return segments
    out: List[Seg] = []
    for s in segments:
        if seg_words(s) <= max_words:
            out.append(s)
            continue
        parts = split_by_punct(s.text)
        if len(parts) <= 1:
            out.append(s)
            continue
        total_words = sum(len(re.findall(r"\w+", p, flags=re.UNICODE)) for p in parts)
        if total_words <= 0:
            out.append(s)
            continue
        t0 = s.start
        dur = seg_duration(s)
        acc = 0.0
        for p in parts:
            pw = len(re.findall(r"\w+", p, flags=re.UNICODE))
            frac = pw / total_words
            pdur = dur * frac
            out.append(Seg(start=t0 + acc, end=min(s.end, t0 + acc + pdur), text=norm_ws(p)))
            acc += pdur
    return out

# -----------------------------
# Diarização PYANNOTE (opcional)
# -----------------------------

def diarize_pyannote_try(audio_path: Path) -> Tuple[Optional[List[Tuple[float, float, str, float]]], Dict[str, Any]]:
    meta: Dict[str, Any] = {"diarize": "pyannote"}
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or ""
    if not token:
        meta["error"] = "no_hf_token_env"
        return None, meta

    try:
        from pyannote.audio import Pipeline
    except Exception as e:
        meta["error"] = f"import pyannote failed: {repr(e)}"
        return None, meta

    model_id = os.environ.get("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
    meta["model_id"] = model_id

    try:
        try:
            pipeline = Pipeline.from_pretrained(model_id, token=token)
        except TypeError:
            pipeline = Pipeline.from_pretrained(model_id, use_auth_token=token)
    except Exception as e:
        meta["error"] = f"pipeline_load_failed: {repr(e)}"
        return None, meta

    try:
        diar = pipeline(str(audio_path))
    except Exception as e:
        meta["error"] = f"pipeline_run_failed: {repr(e)}"
        return None, meta

    items: List[Tuple[float, float, str, float]] = []
    try:
        for turn, _, label in diar.itertracks(yield_label=True):
            items.append((float(turn.start), float(turn.end), str(label), 0.75))
    except Exception as e:
        meta["error"] = f"itertracks_failed: {repr(e)}"
        return None, meta

    meta["n_turns"] = len(items)
    return items, meta

# -----------------------------
# Diarização local: SpeechBrain ECAPA embeddings + clustering
# -----------------------------

_SB_ENCODER = None
_SB_DEVICE = "cpu"

def _load_sb_encoder() -> Any:
    global _SB_ENCODER
    if _SB_ENCODER is not None:
        return _SB_ENCODER
    from speechbrain.pretrained import EncoderClassifier

    source = os.environ.get("SB_SPKREC_MODEL", "speechbrain/spkrec-ecapa-voxceleb")
    savedir = os.environ.get("SB_CACHE_DIR", "/root/analyze_service/repo/_cache_speechbrain")
    Path(savedir).mkdir(parents=True, exist_ok=True)

    _SB_ENCODER = EncoderClassifier.from_hparams(source=source, savedir=savedir, run_opts={"device": _SB_DEVICE})
    return _SB_ENCODER

def _load_audio_mono_16k(audio_path: Path) -> Tuple["torch.Tensor", int]:
    try:
        import torch
        import torchaudio
        wav, sr = torchaudio.load(str(audio_path))
        if wav.dim() == 2 and wav.size(0) > 1:
            wav = wav.mean(dim=0, keepdim=True)
        elif wav.dim() == 1:
            wav = wav.unsqueeze(0)
        if sr != 16000:
            wav = torchaudio.functional.resample(wav, sr, 16000)
            sr = 16000
        wav = wav.to(dtype=torch.float32)
        return wav, sr
    except Exception:
        import numpy as np
        import soundfile as sf
        import torch
        x, sr = sf.read(str(audio_path), always_2d=False)
        if isinstance(x, np.ndarray) and x.ndim == 2:
            x = x.mean(axis=1)
        if sr != 16000:
            try:
                import librosa
                x = librosa.resample(x.astype("float32"), orig_sr=sr, target_sr=16000)
                sr = 16000
            except Exception:
                pass
        x = x.astype("float32")
        wav = torch.from_numpy(x).unsqueeze(0)
        return wav, sr

def _segment_embedding(
    encoder: Any,
    wav_1ch: "torch.Tensor",
    sr: int,
    start: float,
    end: float,
) -> Optional["torch.Tensor"]:
    import torch
    st = max(0.0, float(start))
    en = max(st, float(end))
    if en - st < 0.35:
        return None
    i0 = int(st * sr)
    i1 = int(en * sr)
    if i1 <= i0:
        return None
    chunk = wav_1ch[:, i0:i1]
    with torch.no_grad():
        emb = encoder.encode_batch(chunk)
    if emb.dim() == 3:
        emb = emb.squeeze(0).squeeze(0)
    elif emb.dim() == 2:
        emb = emb.squeeze(0)
    return emb.detach().cpu()

def diarize_embed_kmeans_try(
    audio_path: Path,
    asr_segments: List[Seg],
    n_speakers: int = 2,
) -> Tuple[Optional[List[Tuple[float, float, str, float]]], Dict[str, Any]]:
    meta: Dict[str, Any] = {"diarize": "embed_kmeans", "tag": "embed_kmeans", "conf": 0.60}

    if not asr_segments or len(asr_segments) < 6:
        meta["error"] = "too_few_asr_segments"
        return None, meta

    try:
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics.pairwise import cosine_distances
    except Exception as e:
        meta["error"] = f"import clustering deps failed: {repr(e)}"
        return None, meta

    try:
        encoder = _load_sb_encoder()
    except Exception as e:
        meta["error"] = f"load_sb_encoder_failed: {repr(e)}"
        return None, meta

    try:
        wav, sr = _load_audio_mono_16k(audio_path)
    except Exception as e:
        meta["error"] = f"load_audio_failed: {repr(e)}"
        return None, meta

    emb_list = []
    seg_idx = []
    for i, s in enumerate(asr_segments):
        emb = _segment_embedding(encoder, wav, sr, s.start, s.end)
        if emb is None:
            continue
        emb_list.append(emb.numpy())
        seg_idx.append(i)

    if len(emb_list) < max(6, n_speakers * 3):
        meta["error"] = f"too_few_embeddings: {len(emb_list)}"
        return None, meta

    import numpy as np
    X = np.stack(emb_list, axis=0)
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    try:
        cl = AgglomerativeClustering(n_clusters=n_speakers, metric="cosine", linkage="average")
        labels = cl.fit_predict(X)
    except TypeError:
        cl = AgglomerativeClustering(n_clusters=n_speakers, affinity="cosine", linkage="average")
        labels = cl.fit_predict(X)

    centers = []
    for k in range(n_speakers):
        idxk = np.where(labels == k)[0]
        if len(idxk) == 0:
            centers.append(np.zeros((X.shape[1],), dtype=np.float32))
        else:
            c = X[idxk].mean(axis=0)
            c = c / (np.linalg.norm(c) + 1e-9)
            centers.append(c)
    centers = np.stack(centers, axis=0)

    d = cosine_distances(X, centers)
    chosen = d[np.arange(len(X)), labels]
    confs = 1.0 - chosen
    confs = np.clip(confs, 0.0, 1.0)
    confs = 0.50 + 0.45 * confs

    for j, i in enumerate(seg_idx):
        asr_segments[i].speaker = f"SPEAKER_{int(labels[j]):02d}"
        asr_segments[i].diarize_conf = float(confs[j])
        asr_segments[i].pseudo_speaker = False

    for i, s in enumerate(asr_segments):
        if i in seg_idx:
            continue
        spk = None
        conf = 0.55
        for k in range(i-1, -1, -1):
            if (k in seg_idx):
                spk = asr_segments[k].speaker
                conf = max(conf, asr_segments[k].diarize_conf)
                break
        if spk is None:
            for k in range(i+1, len(asr_segments)):
                if (k in seg_idx):
                    spk = asr_segments[k].speaker
                    conf = max(conf, asr_segments[k].diarize_conf)
                    break
        if spk is None:
            spk = "SPEAKER_00"
        s.speaker = spk
        s.diarize_conf = float(conf)
        s.pseudo_speaker = False

    turns: List[Tuple[float, float, str, float]] = []
    cur_spk = asr_segments[0].speaker
    cur_st = asr_segments[0].start
    cur_en = asr_segments[0].end
    cur_confs = [asr_segments[0].diarize_conf]

    for i in range(1, len(asr_segments)):
        s = asr_segments[i]
        if s.speaker == cur_spk and (s.start - cur_en) <= 0.9:
            cur_en = max(cur_en, s.end)
            cur_confs.append(s.diarize_conf)
        else:
            c = sum(cur_confs) / max(1, len(cur_confs))
            turns.append((float(cur_st), float(cur_en), str(cur_spk), float(c)))
            cur_spk = s.speaker
            cur_st = s.start
            cur_en = s.end
            cur_confs = [s.diarize_conf]

    c = sum(cur_confs) / max(1, len(cur_confs))
    turns.append((float(cur_st), float(cur_en), str(cur_spk), float(c)))

    meta["n_turns"] = len(turns)
    allc = [t[3] for t in turns]
    allc.sort()
    k = max(1, int(len(allc) * 0.8))
    meta["conf"] = float(sum(allc[:k]) / len(allc[:k]))
    return turns, meta

# -----------------------------
# Diarização fallback por pausas
# -----------------------------

def diarize_turn_taking_fallback(segments: List[Seg]) -> Tuple[List[Tuple[float, float, str, float]], Dict[str, Any]]:
    meta = {"diarize": "fallback_turn_taking", "tag": "turn_taking", "conf": 0.40}
    if not segments:
        return [(0.0, 1e9, "SPEAKER_00", 0.25)], {"diarize": "none", "tag": "mono", "conf": 0.25}

    SWITCH_GAP = 0.45
    MIN_SEG_FOR_SWITCH = 0.90

    current = "SPEAKER_00"
    turns: List[Tuple[float, float, str, float]] = []
    cur_st = segments[0].start
    cur_en = segments[0].end

    for i in range(1, len(segments)):
        prev = segments[i-1]
        s = segments[i]
        gap = max(0.0, s.start - prev.end)

        should_switch = (gap >= SWITCH_GAP and seg_duration(s) >= MIN_SEG_FOR_SWITCH and not is_short_ack(s.text))

        if should_switch:
            turns.append((cur_st, cur_en, current, 0.40))
            current = "SPEAKER_01" if current == "SPEAKER_00" else "SPEAKER_00"
            cur_st = s.start
            cur_en = s.end
        else:
            cur_en = max(cur_en, s.end)

    turns.append((cur_st, cur_en, current, 0.40))
    meta["n_turns"] = len(turns)
    return turns, meta

def assign_speaker_to_segments(
    asr_segments: List[Seg],
    diar_turns: List[Tuple[float, float, str, float]],
    pseudo: bool = False,
) -> Tuple[List[Seg], float]:
    if not asr_segments:
        return [], 0.0
    if not diar_turns:
        for s in asr_segments:
            s.speaker = "SPEAKER_00"
            s.diarize_conf = 0.0
            s.pseudo_speaker = True
        return asr_segments, 0.0

    turns = [(float(st), float(en), str(spk), float(conf)) for (st, en, spk, conf) in diar_turns]
    turns.sort(key=lambda x: x[0])

    def overlap(a0, a1, b0, b1) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    confs = []
    for seg in asr_segments:
        best_spk = None
        best_ov = 0.0
        best_conf = 0.0
        for st, en, spk, conf in turns:
            ov = overlap(seg.start, seg.end, st, en)
            if ov > best_ov:
                best_ov = ov
                best_spk = spk
                best_conf = conf
        if best_spk is None:
            best_spk = "SPEAKER_00"
            best_conf = 0.0
        seg.speaker = best_spk
        seg.diarize_conf = best_conf
        seg.pseudo_speaker = bool(pseudo)
        confs.append(best_conf)

    if confs:
        confs_sorted = sorted(confs)
        k = max(1, int(len(confs_sorted) * 0.8))
        global_conf = sum(confs_sorted[:k]) / len(confs_sorted[:k])
    else:
        global_conf = 0.0
    return asr_segments, clamp01(global_conf)

# -----------------------------
# Roles (ASSIMÉTRICO: protege VENDEDOR)
# -----------------------------
# Regra de ouro:
# - ERRAR CLIENTE -> VENDEDOR é ok (entra "lixo", mas não perde vendedor).
# - ERRAR VENDEDOR -> CLIENTE é perigoso (perde fala do vendedor e derruba SPIN/Ollama).
#
# Então:
# - CLIENTE só quando MUITO certo (ACK/operacional).
# - Smoothing NUNCA joga pra CLIENTE; só puxa "ilhas" para VENDEDOR.

STRONG_VENDOR = [
    r"\bestou (te )?ligando\b",
    r"\bestou entrando em contato\b",
    r"\baqui é\b",
    r"\bmeu nome é\b",
    r"\bfalo com\b",
    r"\bposso falar com\b",
    r"\beu gostaria de falar\b",
    r"\btenho o cadastro de vocês\b",
    r"\bqueria entender\b",
    r"\bboa (tarde|noite|dia)\b",
]

STRONG_CLIENT = [
    r"^\s*(sim|não|nao|ok|certo|perfeito|entendi|beleza|tá|ta|uhum|hum|isso|claro|pois não)\s*[\.!\?]*\s*$",
    r"^\s*(tudo (bem|bom)|tô bem|to bem|tudo ótimo|tudo otimo)\s*[\.!\?]*\s*$",
    r"\bcomo posso ajudar\b",
    r"\b(como|em que) posso (ajudar|te ajudar)\b",
    r"\bsó um momento\b",
    r"\bsó um instante\b",
    r"\bdeixa eu confirmar\b",
    r"\bvou confirmar\b",
    r"\bvou verificar\b",
    r"\bdeixa eu verificar\b",
]

QUESTION_WORDS = re.compile(r"\b(qual|como|quanto|quantos|quando|onde|quem|por que|porque)\b", re.IGNORECASE)
HAS_QMARK = re.compile(r"\?\s*$")

def _is_strong_client(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    for pat in STRONG_CLIENT:
        if re.search(pat, t, flags=re.IGNORECASE | re.UNICODE):
            return True
    return False

def _is_strong_vendor(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    for pat in STRONG_VENDOR:
        if re.search(pat, t, flags=re.IGNORECASE | re.UNICODE):
            return True
    return False

def strong_override_role(text: str) -> Optional[str]:
    """
    Override ASSIMÉTRICO:
    - CLIENTE só quando for MUITO certo (ACK/operacional).
    - VENDEDOR quando for bem típico de abordagem.
    """
    t = (text or "").strip()
    if not t:
        return None

    if _is_strong_client(t):
        return "CLIENTE"
    if _is_strong_vendor(t):
        return "VENDEDOR"
    return None

def compute_speaker_points(segments: List[Seg]) -> Dict[str, float]:
    points: Dict[str, float] = {}
    for seg in segments:
        points.setdefault(seg.speaker, 5.0)

    for seg in segments:
        t = seg.text or ""
        tl = t.lower()
        spk = seg.speaker

        # perguntas -> vendedor (evita dar boost em ACK com "?")
        if (HAS_QMARK.search(t) or QUESTION_WORDS.search(tl)) and not is_short_ack(t):
            points[spk] += 0.85

        # frases típicas de vendedor
        if re.search(r"\b(boa tarde|boa noite|bom dia)\b", tl):
            points[spk] += 0.45
        if re.search(r"\b(estou entrando em contato|posso falar com|meu nome|aqui é|falo com|cadastro de vocês|estou te ligando)\b", tl):
            points[spk] += 1.60

        if re.search(r"\b(você|vocês)\b", tl):
            points[spk] += 0.15

        # ACK curto -> tende a cliente (penaliza pra não virar vendedor)
        if is_short_ack(t):
            points[spk] -= 0.75

        # operacional do cliente -> penaliza mais
        if re.search(r"\b(confirmar|verificar|um momento|só um instante|só um momento)\b", tl):
            points[spk] -= 1.35

        w = seg_words(seg)
        if w >= 14:
            points[spk] += 0.10
        if w <= 3:
            points[spk] -= 0.25

    return points

def pick_roles_from_points(points: Dict[str, float]) -> Dict[str, str]:
    if not points:
        return {"SPEAKER_00": "VENDEDOR"}
    best_spk = max(points.items(), key=lambda kv: kv[1])[0]
    return {spk: ("VENDEDOR" if spk == best_spk else "CLIENTE") for spk in points.keys()}

def opening_repairs(segments: List[Seg], opening_secs: float = ROLE_SMOOTH_OPENING_SECS) -> Tuple[List[Seg], List[Dict[str, Any]]]:
    dbg = []
    idxs = [i for i, s in enumerate(segments) if s.start <= opening_secs]
    if len(idxs) < 4:
        return segments, dbg

    # força vendedor na abertura quando for típico
    for i in idxs:
        if _is_strong_vendor(segments[i].text) and segments[i].role != "VENDEDOR":
            old = segments[i].role
            segments[i].role = "VENDEDOR"
            segments[i].opening_repair = True
            segments[i].role_override = True
            dbg.append({"idx": i, "reason": "opening_force_vendor_phrase", "old": old, "new": "VENDEDOR"})

    # ACK depois de "tudo bem?" -> CLIENTE (somente se for ACK forte)
    for i in idxs[1:]:
        prev = segments[i-1]
        cur = segments[i]
        if re.search(r"tudo bem\??", (prev.text or "").lower()) and _is_strong_client(cur.text):
            if cur.role != "CLIENTE":
                old = cur.role
                cur.role = "CLIENTE"
                cur.opening_repair = True
                cur.role_override = True
                dbg.append({"idx": i, "reason": "opening_ack_client_strong", "old": old, "new": "CLIENTE"})

    return segments, dbg

def _allow_role_smoothing(seg: Seg, global_conf: float) -> bool:
    if bool(getattr(seg, "pseudo_speaker", False)):
        return True
    if float(global_conf) < ROLE_SMOOTH_MIN_GLOBAL_CONF:
        return True
    if float(getattr(seg, "diarize_conf", 0.0)) < ROLE_SMOOTH_MIN_DIAR_CONF:
        return True
    if float(seg.start) <= ROLE_SMOOTH_OPENING_SECS:
        if seg_duration(seg) <= ROLE_SMOOTH_MAX_DUR or seg_words(seg) <= ROLE_SMOOTH_MAX_WORDS:
            return True
    return False

def smooth_roles(segments: List[Seg], global_conf: float) -> Tuple[List[Seg], List[Dict[str, Any]]]:
    dbg = []
    if len(segments) < 3:
        return segments, dbg

    for i in range(1, len(segments)-1):
        s = segments[i]

        if seg_words(s) > ROLE_SMOOTH_MAX_WORDS and seg_duration(s) > ROLE_SMOOTH_MAX_DUR:
            continue

        left = segments[i-1].role
        right = segments[i+1].role

        # Só puxa ilha para VENDEDOR
        if left == "VENDEDOR" and right == "VENDEDOR" and s.role != "VENDEDOR":
            if s.role_override:
                dbg.append({"idx": i, "reason": "role_smoothing_skipped_override", "old": s.role, "new": s.role})
                continue
            if not _allow_role_smoothing(s, global_conf):
                dbg.append({"idx": i, "reason": "role_smoothing_skipped_high_conf", "old": s.role, "new": s.role})
                continue
            if _is_strong_client(s.text):
                dbg.append({"idx": i, "reason": "role_smoothing_skipped_strong_client", "old": s.role, "new": s.role})
                continue

            old = s.role
            s.role = "VENDEDOR"
            s.opening_repair = s.opening_repair or (s.start <= ROLE_SMOOTH_OPENING_SECS)
            dbg.append({"idx": i, "reason": "role_smoothing_island_to_vendor", "old": old, "new": "VENDEDOR"})

    return segments, dbg

def apply_roles(segments: List[Seg], diarize_exists: bool, global_conf: float) -> Tuple[List[Seg], Dict[str, Any]]:
    debug: Dict[str, Any] = {
        "speaker_points": {},
        "spk_to_role": {},
        "role_overrides": [],
        "debug_opening_repairs": [],
        "debug_role_smoothing": [],
    }
    if not segments:
        return segments, debug

    points = compute_speaker_points(segments)
    debug["speaker_points"] = {k: round(v, 3) for k, v in points.items()}

    spk_to_role = pick_roles_from_points(points)
    debug["spk_to_role"] = spk_to_role

    # base por speaker (sempre)
    for s in segments:
        s.role = spk_to_role.get(s.speaker, "VENDEDOR")

    # Override por texto (ASSIMÉTRICO):
    # - CLIENTE: só se strong_client e só quando diarização for fraca/pseudo
    # - VENDEDOR: pode reforçar quando diarização é fraca/pseudo
    for i, s in enumerate(segments):
        ov = strong_override_role(s.text)
        if not ov:
            continue

        if ov == "CLIENTE":
            if not _is_strong_client(s.text):
                continue
            allow_client = (not diarize_exists) or bool(s.pseudo_speaker) or (float(global_conf) < 0.62) or (float(s.diarize_conf) < 0.62)
            if not allow_client:
                continue
            if s.role != "CLIENTE":
                old = s.role
                s.role = "CLIENTE"
                s.role_override = True
                debug["role_overrides"].append({
                    "idx": i,
                    "start": s.start,
                    "end": s.end,
                    "speaker": s.speaker,
                    "text": (s.text or "")[:180],
                    "old_role": old,
                    "new_role": "CLIENTE",
                    "reason": "strong_client_override_asymmetric",
                })
            continue

        if ov == "VENDEDOR":
            allow_vendor = (not diarize_exists) or (float(global_conf) < 0.70) or bool(s.pseudo_speaker) or (float(s.diarize_conf) < 0.62)
            if allow_vendor and s.role != "VENDEDOR":
                old = s.role
                s.role = "VENDEDOR"
                s.role_override = True
                debug["role_overrides"].append({
                    "idx": i,
                    "start": s.start,
                    "end": s.end,
                    "speaker": s.speaker,
                    "text": (s.text or "")[:180],
                    "old_role": old,
                    "new_role": "VENDEDOR",
                    "reason": "strong_vendor_override",
                })

    segments, open_dbg = opening_repairs(segments, opening_secs=ROLE_SMOOTH_OPENING_SECS)
    debug["debug_opening_repairs"] = open_dbg

    segments, sm_dbg = smooth_roles(segments, global_conf=global_conf)
    debug["debug_role_smoothing"] = sm_dbg

    return segments, debug

# -----------------------------
# Diarize AUTO (ordem boa)
# -----------------------------

def diarize_auto(audio_path: Path, asr_segments: List[Seg], n_speakers: int = 2) -> Tuple[List[Tuple[float, float, str, float]], Dict[str, Any], bool]:
    """
    Retorna: (turns, meta, pseudo)
    pseudo=True apenas em turn_taking.
    """
    turns, meta = diarize_embed_kmeans_try(audio_path, asr_segments, n_speakers=n_speakers)
    if turns:
        return turns, meta, False

    py_turns, py_meta = diarize_pyannote_try(audio_path)
    if py_turns:
        py_meta["tag"] = "pyannote"
        py_meta["conf"] = 0.80
        return py_turns, py_meta, False

    tt_turns, tt_meta = diarize_turn_taking_fallback(asr_segments)
    tt_meta["pyannote_error"] = py_meta.get("error")
    tt_meta["pyannote_model_id"] = py_meta.get("model_id")
    if meta.get("error"):
        tt_meta["embed_kmeans_error"] = meta.get("error")
    return tt_turns, tt_meta, True

# -----------------------------
# CLI / Main (continua na PARTE 2)
# -----------------------------
# ==============================
# PARTE 2/2 — CLI + MAIN (ATUALIZADA E COMPLETA)
# Cole e SUBSTITUA sua parte 2 inteira por esta
# ==============================

# ==============================
# PARTE 2/2 — CLI + MAIN (ATUALIZADA E COMPLETA)
# Cole e SUBSTITUA sua parte 2 inteira por esta
# ==============================

# -----------------------------
# Constantes default (tuning)
# -----------------------------

# Role smoothing (evita mexer quando diarização é boa)
ROLE_SMOOTH_MIN_DIAR_CONF = 0.78          # se seg.diarize_conf >= isso, evita mexer no role (fora abertura)
ROLE_SMOOTH_MIN_GLOBAL_CONF = 0.74        # se global >= isso, evita mexer em “ilhas” com muita confiança
ROLE_SMOOTH_OPENING_SECS = 45.0           # janela de abertura para reparos
ROLE_SMOOTH_MAX_DUR = 3.2                 # só mexe em segmentos curtos
ROLE_SMOOTH_MAX_WORDS = 7                 # "ilha" pequena = <= 7 palavras

# Speaker fix (ASSIMÉTRICO: protege VENDEDOR)
SPEAKER_FIX_ENABLED_DEFAULT = True
SPEAKER_FIX_MIN_GLOBAL_CONF = 0.68        # só tenta corrigir speaker se global >= esse limiar
SPEAKER_FIX_MIN_SEG_CONF = 0.70           # só mexe em segmentos com diarize_conf >= isso
SPEAKER_FIX_MIN_POINT_GAP = 3.0           # diferença mínima de pontos entre speakers
SPEAKER_FIX_MAX_RUN_SECS = 12.0           # não corrigir bloco enorme
SPEAKER_FIX_MAX_RUN_SEGS = 4              # nem muitos segmentos
SPEAKER_FIX_VENDOR_STRONG_ONLY = True     # se True, só corrige quando texto bate em _is_strong_vendor()

# -----------------------------
# Argparse / helpers main
# -----------------------------

def build_argparser():
    ap = argparse.ArgumentParser()

    ap.add_argument("--input_dir", default="/root/analyze_service/repo/arquivos_audio")
    ap.add_argument("--out_txt_dir", default="/root/analyze_service/repo/arquivos_transcritos/txt/_tmp_transc_test")
    ap.add_argument("--out_json_dir", default="/root/analyze_service/repo/arquivos_transcritos/json/_tmp_transc_test")
    ap.add_argument("--only_file", default="", help="Processa apenas este arquivo (nome ou caminho).")

    # ASR
    ap.add_argument("--fw_model", default="small")
    ap.add_argument("--fw_compute", default="int8")
    ap.add_argument("--fw_beam", type=int, default=1)
    ap.add_argument("--fw_no_prev_text", action="store_true")
    ap.add_argument("--fw_language", default="pt")
    ap.add_argument("--vad_aggressive", type=int, default=2, help="0..3")
    ap.add_argument("--split_by_punct", action="store_true")
    ap.add_argument("--max_words_split", type=int, default=26)

    # diarização
    ap.add_argument("--diarize", default="auto", choices=["auto", "pyannote", "embed_kmeans", "turn_taking", "none"])
    ap.add_argument("--n_speakers", type=int, default=2, help="fixa n speakers no embed_kmeans (default 2)")

    # dicionário
    ap.add_argument("--dict_path", default="/root/analyze_service/repo/assets/transcribe_dict.txt")

    # speaker fix (liga/desliga)
    ap.add_argument(
        "--speaker_fix",
        type=int,
        default=(1 if SPEAKER_FIX_ENABLED_DEFAULT else 0),
        help="1=ativa correção de SPEAKER por texto, 0=desativa",
    )

    # speaker fix thresholds (opcionais)
    ap.add_argument("--speaker_fix_min_global_conf", type=float, default=SPEAKER_FIX_MIN_GLOBAL_CONF)
    ap.add_argument("--speaker_fix_min_seg_conf", type=float, default=SPEAKER_FIX_MIN_SEG_CONF)
    ap.add_argument("--speaker_fix_min_point_gap", type=float, default=SPEAKER_FIX_MIN_POINT_GAP)
    ap.add_argument("--speaker_fix_max_run_secs", type=float, default=SPEAKER_FIX_MAX_RUN_SECS)
    ap.add_argument("--speaker_fix_max_run_segs", type=int, default=SPEAKER_FIX_MAX_RUN_SEGS)
    ap.add_argument("--speaker_fix_vendor_strong_only", type=int, default=(1 if SPEAKER_FIX_VENDOR_STRONG_ONLY else 0))

    # role smoothing thresholds (opcionais)
    ap.add_argument("--role_smooth_min_diar_conf", type=float, default=ROLE_SMOOTH_MIN_DIAR_CONF)
    ap.add_argument("--role_smooth_min_global_conf", type=float, default=ROLE_SMOOTH_MIN_GLOBAL_CONF)
    ap.add_argument("--role_smooth_opening_secs", type=float, default=ROLE_SMOOTH_OPENING_SECS)
    ap.add_argument("--role_smooth_max_dur", type=float, default=ROLE_SMOOTH_MAX_DUR)
    ap.add_argument("--role_smooth_max_words", type=int, default=ROLE_SMOOTH_MAX_WORDS)

    return ap


def resolve_only_file(input_dir: Path, only_file: str) -> List[Path]:
    exts = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    if not only_file:
        files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in exts]
        return sorted(files)

    p = Path(only_file)
    if p.exists() and p.is_file() and p.suffix.lower() in exts:
        return [p]

    q = input_dir / only_file
    if q.exists() and q.is_file() and q.suffix.lower() in exts:
        return [q]

    matches = [m for m in input_dir.glob(f"*{only_file}*") if m.is_file() and m.suffix.lower() in exts]
    return sorted(matches)[:1]


def _vad_params_from_aggressive(level: int) -> Dict[str, Any]:
    """
    Presets simples pra VAD do faster-whisper.
    Quanto maior o level, mais agressivo (corta mais silêncio / divide mais).
    """
    if level >= 3:
        return {"min_silence_duration_ms": 220, "speech_pad_ms": 90}
    if level == 2:
        return {"min_silence_duration_ms": 320, "speech_pad_ms": 140}
    if level == 1:
        return {"min_silence_duration_ms": 480, "speech_pad_ms": 190}
    return {"min_silence_duration_ms": 650, "speech_pad_ms": 240}


def _spk_other(spk: str, speakers: List[str]) -> Optional[str]:
    for s in speakers:
        if s != spk:
            return s
    return None


# -----------------------------
# Speaker Fix (ASSIMÉTRICO: só corrige para o vendedor)
# -----------------------------

def speaker_text_correction_vendor_only(
    segments: List[Seg],
    speaker_points: Dict[str, float],
    diar_global_conf: float,
    diarize_exists: bool,
    enabled: bool,
    min_global_conf: float,
    min_seg_conf: float,
    min_point_gap: float,
    max_run_secs: float,
    max_run_segs: int,
    vendor_strong_only: bool,
) -> Tuple[List[Seg], List[Dict[str, Any]]]:
    """
    Corrige swaps locais SEM RISCO de perder vendedor:
    - Só corrige quando o texto é (fortemente) de VENDEDOR
    - Move o SPEAKER do segmento (ou run curto) para o SPEAKER do vendedor global (best_spk)
    - NUNCA corrige "para cliente"
    """
    dbg: List[Dict[str, Any]] = []
    if not enabled:
        return segments, dbg
    if not segments or not diarize_exists:
        return segments, dbg
    if float(diar_global_conf) < float(min_global_conf):
        return segments, dbg
    if not speaker_points or len(speaker_points) < 2:
        return segments, dbg

    speakers = sorted(list({s.speaker for s in segments}))
    if len(speakers) < 2:
        return segments, dbg

    best_spk = max(speaker_points.items(), key=lambda kv: kv[1])[0]
    worst_spk = min(speaker_points.items(), key=lambda kv: kv[1])[0]
    gap = float(speaker_points.get(best_spk, 0.0) - speaker_points.get(worst_spk, 0.0))
    if gap < float(min_point_gap):
        return segments, dbg

    def looks_like_vendor(text: str) -> bool:
        # Usa os helpers da Parte 1 (assume que existem no escopo)
        if vendor_strong_only:
            return bool(_is_strong_vendor(text))
        # modo mais permissivo: pergunta não-ACK também sugere vendedor
        t = (text or "").strip()
        if not t:
            return False
        if _is_strong_vendor(t):
            return True
        if (HAS_QMARK.search(t) or QUESTION_WORDS.search(t.lower())) and not is_short_ack(t) and len(t) >= 14:
            return True
        return False

    i = 0
    while i < len(segments):
        s = segments[i]

        # Só mexe em segmentos com diarize_conf ok (modelo "confiante" mas pode ter swap local)
        if float(getattr(s, "diarize_conf", 0.0) or 0.0) < float(min_seg_conf):
            i += 1
            continue

        if not looks_like_vendor(s.text):
            i += 1
            continue

        # Se já está no speaker do vendedor global, ok
        if s.speaker == best_spk:
            i += 1
            continue

        # monta run curto, só se continuar parecendo vendedor
        run_idxs = [i]
        run_secs = seg_duration(s)
        j = i + 1

        while j < len(segments) and len(run_idxs) < int(max_run_segs) and run_secs < float(max_run_secs):
            sj = segments[j]
            if sj.speaker != s.speaker:
                break
            if float(getattr(sj, "diarize_conf", 0.0) or 0.0) < float(min_seg_conf):
                break
            if not looks_like_vendor(sj.text):
                break
            run_idxs.append(j)
            run_secs += seg_duration(sj)
            j += 1

        old_spk = s.speaker
        for k in run_idxs:
            segments[k].speaker = best_spk

        dbg.append({
            "idxs": run_idxs,
            "reason": "speaker_text_correction_vendor_only",
            "from_speaker": old_spk,
            "to_speaker": best_spk,
            "run_secs": round(float(run_secs), 3),
            "global_conf": round(float(diar_global_conf), 3),
            "points_gap": round(float(gap), 3),
            "example_text": (segments[i].text or "")[:180],
        })

        i = run_idxs[-1] + 1

    return segments, dbg


# -----------------------------
# Main
# -----------------------------

def main():
    args = build_argparser().parse_args()

    # aplica tuning CLI nas globals usadas pela Parte 1 (smooth/opening/etc.)
    global ROLE_SMOOTH_MIN_DIAR_CONF, ROLE_SMOOTH_MIN_GLOBAL_CONF, ROLE_SMOOTH_OPENING_SECS, ROLE_SMOOTH_MAX_DUR, ROLE_SMOOTH_MAX_WORDS
    ROLE_SMOOTH_MIN_DIAR_CONF = float(args.role_smooth_min_diar_conf)
    ROLE_SMOOTH_MIN_GLOBAL_CONF = float(args.role_smooth_min_global_conf)
    ROLE_SMOOTH_OPENING_SECS = float(args.role_smooth_opening_secs)
    ROLE_SMOOTH_MAX_DUR = float(args.role_smooth_max_dur)
    ROLE_SMOOTH_MAX_WORDS = int(args.role_smooth_max_words)

    input_dir = Path(args.input_dir)
    out_txt_dir = Path(args.out_txt_dir)
    out_json_dir = Path(args.out_json_dir)

    safe_mkdir(out_txt_dir)
    safe_mkdir(out_json_dir)

    dict_path = Path(args.dict_path)
    dict_rules = load_replacement_dict(dict_path)

    files = resolve_only_file(input_dir, args.only_file)
    if not files:
        print(f"[01] Nenhum arquivo encontrado em {input_dir} (only_file={args.only_file!r})")
        return 2

    vad_params = _vad_params_from_aggressive(int(args.vad_aggressive))
    do_speaker_fix = bool(int(getattr(args, "speaker_fix", 1)))

    # speaker fix thresholds (do CLI)
    sp_min_global = float(getattr(args, "speaker_fix_min_global_conf", SPEAKER_FIX_MIN_GLOBAL_CONF))
    sp_min_seg = float(getattr(args, "speaker_fix_min_seg_conf", SPEAKER_FIX_MIN_SEG_CONF))
    sp_min_gap = float(getattr(args, "speaker_fix_min_point_gap", SPEAKER_FIX_MIN_POINT_GAP))
    sp_max_secs = float(getattr(args, "speaker_fix_max_run_secs", SPEAKER_FIX_MAX_RUN_SECS))
    sp_max_segs = int(getattr(args, "speaker_fix_max_run_segs", SPEAKER_FIX_MAX_RUN_SEGS))
    sp_vendor_strong_only = bool(int(getattr(args, "speaker_fix_vendor_strong_only", 1)))

    for audio_path in files:
        stem = audio_path.stem

        # -----------------
        # 1) ASR
        # -----------------
        asr_segments, asr_meta = transcribe_faster_whisper(
            audio_path=audio_path,
            model_name=args.fw_model,
            compute_type=args.fw_compute,
            beam_size=args.fw_beam,
            condition_on_previous_text=(not args.fw_no_prev_text),
            vad_filter=True,
            vad_parameters=vad_params,
            language=args.fw_language or "pt",
        )

        txt_out = out_txt_dir / f"{stem}.txt"
        json_out = out_json_dir / f"{stem}.json"

        if not asr_segments:
            write_text(txt_out, "")
            payload = {
                "file": str(audio_path.name),
                "asr": asr_meta,
                "diarize": {"tag": "mono", "conf": 0.0, "global_conf_from_turns": 0.0, "pyannote_error": None, "meta": {"diarize": "none"}},
                "spk_to_role": {"SPEAKER_00": "VENDEDOR"},
                "speaker_points": {"SPEAKER_00": 5.0},
                "segments": [],
                "debug": {
                    "dict_path": str(dict_path),
                    "dict_rules_n": int(len(dict_rules)),
                    "dict_repairs": [],
                    "diarize_turns_preview": [],
                    "diarize_speakers": ["SPEAKER_00"],
                    "diarize_exists": False,
                    "pseudo_speaker_mode": True,

                    "speaker_fix_enabled": bool(do_speaker_fix),
                    "speaker_fix_debug": [],
                    "speaker_points_pre": {},

                    "role_overrides": [],
                    "debug_opening_repairs": [],
                    "debug_role_smoothing": [],

                    "role_smoothing_thresholds": {
                        "min_seg_conf": ROLE_SMOOTH_MIN_DIAR_CONF,
                        "min_global_conf": ROLE_SMOOTH_MIN_GLOBAL_CONF,
                        "opening_secs": ROLE_SMOOTH_OPENING_SECS,
                        "max_dur": ROLE_SMOOTH_MAX_DUR,
                        "max_words": ROLE_SMOOTH_MAX_WORDS,
                    },
                    "speaker_fix_thresholds": {
                        "enabled": bool(do_speaker_fix),
                        "min_global_conf": sp_min_global,
                        "min_seg_conf": sp_min_seg,
                        "min_point_gap": sp_min_gap,
                        "max_run_secs": sp_max_secs,
                        "max_run_segs": sp_max_segs,
                        "vendor_strong_only": sp_vendor_strong_only,
                    },
                },
            }
            write_json(json_out, payload)
            print(f"[01] OK (ASR vazio): {audio_path.name}")
            print(f"     TXT : {txt_out}")
            print(f"     JSON: {json_out}")
            continue

        # split longos antes da diarização (ajuda clustering)
        asr_segments = explode_long_segments(asr_segments, args.split_by_punct, max_words=args.max_words_split)

        # -----------------
        # 2) DIARIZAÇÃO
        # -----------------
        diar_turns: List[Tuple[float, float, str, float]] = []
        diar_meta: Dict[str, Any] = {}
        pseudo = False

        try:
            if args.diarize == "none":
                diar_turns = [(0.0, 1e9, "SPEAKER_00", 0.25)]
                diar_meta = {"diarize": "none", "tag": "mono", "conf": 0.25}
                pseudo = True
            elif args.diarize == "turn_taking":
                diar_turns, diar_meta = diarize_turn_taking_fallback(asr_segments)
                pseudo = True
            elif args.diarize == "pyannote":
                t, m = diarize_pyannote_try(audio_path)
                diar_turns = t or [(0.0, 1e9, "SPEAKER_00", 0.25)]
                diar_meta = m
                diar_meta.setdefault("tag", "pyannote")
                diar_meta.setdefault("conf", 0.80 if t else 0.25)
                pseudo = False
            elif args.diarize == "embed_kmeans":
                t, m = diarize_embed_kmeans_try(audio_path, asr_segments, n_speakers=args.n_speakers)
                diar_turns = t or [(0.0, 1e9, "SPEAKER_00", 0.25)]
                diar_meta = m
                diar_meta.setdefault("tag", "embed_kmeans")
                diar_meta.setdefault("conf", float(diar_meta.get("conf", 0.60)) if t else 0.25)
                pseudo = False
            else:
                diar_turns, diar_meta, pseudo = diarize_auto(audio_path, asr_segments, n_speakers=args.n_speakers)
        except Exception as e:
            diar_turns = [(0.0, 1e9, "SPEAKER_00", 0.25)]
            diar_meta = {"diarize": "none", "tag": "mono", "conf": 0.25, "error": f"diarize_exception: {repr(e)}"}
            pseudo = True

        uniq_spk = sorted({t[2] for t in diar_turns})
        diarize_exists = (diar_meta.get("tag") not in (None, "mono")) and (len(uniq_spk) > 1)

        # -----------------
        # 3) Atribui speaker por overlap
        # -----------------
        asr_segments, diar_global_conf = assign_speaker_to_segments(asr_segments, diar_turns, pseudo=pseudo)

        # -----------------
        # 4) Dicionário (antes de pontos/roles)
        # -----------------
        dict_repairs_all = []
        if dict_rules:
            for seg in asr_segments:
                new_txt, repairs = apply_replacement_dict(seg.text, dict_rules)
                if repairs:
                    dict_repairs_all.append({
                        "start": round(seg.start, 3),
                        "end": round(seg.end, 3),
                        "speaker": seg.speaker,
                        "before": (seg.text or "")[:180],
                        "after": (new_txt or "")[:180],
                        "repairs": repairs,
                    })
                seg.text = new_txt
        else:
            for seg in asr_segments:
                seg.text = norm_ws(seg.text)

        # -----------------
        # 5) Pré-roles: pontos cedo (pro speaker_fix)
        # -----------------
        speaker_points_pre = compute_speaker_points(asr_segments)

        # -----------------
        # 6) Speaker Fix (ASSIMÉTRICO: só corrige para vendedor)
        # -----------------
        speaker_fix_debug = []
        if do_speaker_fix:
            asr_segments, speaker_fix_debug = speaker_text_correction_vendor_only(
                segments=asr_segments,
                speaker_points=speaker_points_pre,
                diar_global_conf=float(diar_global_conf),
                diarize_exists=bool(diarize_exists),
                enabled=True,
                min_global_conf=sp_min_global,
                min_seg_conf=sp_min_seg,
                min_point_gap=sp_min_gap,
                max_run_secs=sp_max_secs,
                max_run_segs=sp_max_segs,
                vendor_strong_only=sp_vendor_strong_only,
            )
            # recalcula pontos depois do fix (pra debug e consistência)
            speaker_points_pre = compute_speaker_points(asr_segments)

        # -----------------
        # 7) Roles (AGORA sim)
        # -----------------
        asr_segments, roles_debug = apply_roles(asr_segments, diarize_exists=diarize_exists, global_conf=diar_global_conf)

        # -----------------
        # 8) TXT
        # -----------------
        txt_lines = []
        for seg in asr_segments:
            role = seg.role if seg.role in ("VENDEDOR", "CLIENTE") else "VENDEDOR"
            txt_lines.append(f"[{role}] {seg.text}")
        write_text(txt_out, "\n".join(txt_lines).strip() + "\n")

        # -----------------
        # 9) JSON debug rico
        # -----------------
        turns_preview = []
        for (st, en, spk, conf) in diar_turns[:60]:
            turns_preview.append({
                "start": round(float(st), 3),
                "end": round(float(en), 3),
                "speaker": str(spk),
                "conf": round(float(conf), 3),
            })

        pyannote_error = None
        if "pyannote" in str(diar_meta.get("diarize", "")) or diar_meta.get("tag") == "pyannote":
            pyannote_error = diar_meta.get("error")
        if diar_meta.get("pyannote_error"):
            pyannote_error = diar_meta.get("pyannote_error")

        payload = {
            "file": str(audio_path.name),
            "asr": asr_meta,
            "diarize": {
                "tag": diar_meta.get("tag", diar_meta.get("diarize", "unknown")),
                "conf": round(float(diar_meta.get("conf", diar_global_conf)), 3),
                "global_conf_from_turns": round(float(diar_global_conf), 3),
                "pyannote_error": pyannote_error,
                "meta": diar_meta,
            },
            "spk_to_role": roles_debug.get("spk_to_role", {}),
            "speaker_points": roles_debug.get("speaker_points", {}),
            "segments": [
                {
                    "start": round(s.start, 3),
                    "end": round(s.end, 3),
                    "speaker": s.speaker,
                    "diarize_conf": round(float(s.diarize_conf), 3),
                    "pseudo_speaker": bool(s.pseudo_speaker),
                    "role": s.role,
                    "role_override": bool(s.role_override),
                    "opening_repair": bool(s.opening_repair),
                    "text": s.text,
                }
                for s in asr_segments
            ],
            "debug": {
                "dict_path": str(dict_path),
                "dict_rules_n": int(len(dict_rules)),
                "dict_repairs": dict_repairs_all[:250],

                "diarize_turns_preview": turns_preview,
                "diarize_speakers": uniq_spk,
                "diarize_exists": bool(diarize_exists),
                "pseudo_speaker_mode": bool(pseudo),

                "speaker_fix_enabled": bool(do_speaker_fix),
                "speaker_fix_debug": speaker_fix_debug[:250],
                "speaker_points_pre": {k: round(v, 3) for k, v in speaker_points_pre.items()},

                "role_overrides": roles_debug.get("role_overrides", []),
                "debug_opening_repairs": roles_debug.get("debug_opening_repairs", []),
                "debug_role_smoothing": roles_debug.get("debug_role_smoothing", []),

                "role_smoothing_thresholds": {
                    "min_seg_conf": ROLE_SMOOTH_MIN_DIAR_CONF,
                    "min_global_conf": ROLE_SMOOTH_MIN_GLOBAL_CONF,
                    "opening_secs": ROLE_SMOOTH_OPENING_SECS,
                    "max_dur": ROLE_SMOOTH_MAX_DUR,
                    "max_words": ROLE_SMOOTH_MAX_WORDS,
                },
                "speaker_fix_thresholds": {
                    "enabled": bool(do_speaker_fix),
                    "min_global_conf": sp_min_global,
                    "min_seg_conf": sp_min_seg,
                    "min_point_gap": sp_min_gap,
                    "max_run_secs": sp_max_secs,
                    "max_run_segs": sp_max_segs,
                    "vendor_strong_only": sp_vendor_strong_only,
                },
            },
        }

        write_json(json_out, payload)

        print(f"[01] OK: {audio_path.name}")
        print(f"     TXT : {txt_out}")
        print(f"     JSON: {json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

