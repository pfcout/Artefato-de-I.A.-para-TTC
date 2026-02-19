#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts_base/01_transcricao.py — SPIN Analyzer (LOCAL Windows) — ASR faster-whisper + (Opcional) pyannote diarização
Robustez operacional: nunca travar pipeline; sempre gerar TXT + JSON.

Regras fixas:
- Saída obrigatória sempre:
  - TXT em arquivos_transcritos/txt
  - JSON em arquivos_transcritos/json
- Rótulos:
  - Se diarização confiável: [VENDEDOR] e [CLIENTE]
    - Regra Coutinho (fixa): SPEAKER_00 => VENDEDOR | SPEAKER_01 => CLIENTE
    - Outros speakers => CLIENTE
  - Se não houver diarização/token/erro: tudo como [VENDEDOR] (fallback automático)
- Diarização só é considerada OK se houver >=2 speakers.
- HF_TOKEN opcional:
  - Se presente e funcionar: usa pyannote
  - Se ausente/erro/gated: fallback total vendedor
- Cache "não reprocessar":
  - Pasta crachedbl/ (exatamente este nome)
  - SQLite em crachedbl/cache.db
  - Key = sha256(audio_bytes) + sha256(params relevantes)
  - Se já processado e sem --force: não reprocessa; regera TXT/JSON do cache
  - Após gerar saída: arquiva o áudio para crachedbl/

Auto GPU:
- --device auto (default): usa cuda se disponível, senão cpu
- --device cuda: tenta cuda, se não houver, cai para cpu sem quebrar
- --device cpu: força cpu

Correções críticas implementadas:
- Remove dependência de torchaudio/torchcodec no preload (Windows):
  - Preload prioritário: soundfile (libsndfile)
  - Fallback: wave (somente WAV PCM)
- Autenticação do pyannote compatível com versões diferentes: tenta token=, hf_token=, use_auth_token=
- Compatibilidade com retorno do pipeline (pyannote 3.x e 4.x):
  - Pode retornar Annotation direta OU DiarizeOutput com .speaker_diarization / .exclusive_speaker_diarization / .annotation
- Lógica Coutinho: NÃO renomeia por duração. Mantém speaker 0/1 como 00/01 e demais como CLIENTE.
- Heartbeat contínuo em ASR e diarização para garantir “não congelou”
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

warnings.filterwarnings("ignore", message=r".*torchcodec is not installed correctly.*")

try:
    from deepmultilingualpunctuation import PunctuationModel  # type: ignore
    _PUNCT_MODEL = PunctuationModel()
except Exception:
    _PUNCT_MODEL = None

try:
    from fuzzywuzzy import fuzz  # type: ignore
except Exception:
    fuzz = None

_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".mp4"}
DEFAULT_LANG = "pt"

CACHE_DIR_NAME = "crachedbl"
CACHE_DB_NAME = "cache.db"


def _now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def _parse_bool(s: str) -> bool:
    return str(s).strip().lower() in {"1", "true", "t", "yes", "y", "sim"}


def _safe_filename(name: str) -> str:
    name = name.strip().replace("\n", " ").replace("\r", " ")
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "audio"


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = seconds - 60 * m
    return f"{m}m{s:04.1f}s"


def _try_get_wav_duration_seconds(path: Path) -> Optional[float]:
    try:
        import wave
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except Exception:
        return None
    return None


def _resolve_device(device_arg: str) -> str:
    d = (device_arg or "").strip().lower()
    if d in {"", "auto"}:
        try:
            import torch  # type: ignore
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    if d == "cuda":
        try:
            import torch  # type: ignore
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    return "cpu"


def _start_heartbeat(prefix: str, every_s: float = 15.0) -> Tuple[threading.Event, threading.Thread]:
    stop_evt = threading.Event()
    t0 = time.time()
    last_print = {"t": t0}

    def _run():
        while not stop_evt.is_set():
            time.sleep(0.2)
            now = time.time()
            if now - last_print["t"] >= every_s:
                print(f"  Progresso: {prefix} | tempo decorrido {_format_elapsed(now - t0)}")
                last_print["t"] = now

    th = threading.Thread(target=_run, daemon=True)
    th.start()
    return stop_evt, th


def _stop_heartbeat(stop_evt: threading.Event, th: threading.Thread) -> None:
    try:
        stop_evt.set()
        th.join(timeout=2.0)
    except Exception:
        pass


def carregar_dicionario(dict_path: str) -> Dict[str, str]:
    dicionario: Dict[str, str] = {}
    path = Path(dict_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k and v:
                        dicionario[k] = v
        print(f"Dicionário carregado: {len(dicionario)} entradas.")
    else:
        print("Dicionário não encontrado. Seguindo sem correções lexicais.")
    return dicionario


def aplicar_dicionario(texto: str, dicionario: Dict[str, str], threshold: int = 80) -> Tuple[str, int]:
    texto_corrigido = texto
    n_corrigidas = 0

    texto_normalizado = re.sub(r"[^\w\sÀ-ÿ]", "", texto_corrigido)

    for orig, corr in sorted(dicionario.items(), key=lambda x: len(x[0]), reverse=True):
        padrao = re.compile(rf"\b{re.escape(orig)}\b", flags=re.IGNORECASE)
        novo_texto, n = padrao.subn(corr, texto_corrigido)
        if n > 0:
            n_corrigidas += n
        texto_corrigido = novo_texto

    if fuzz is not None:
        palavras = re.findall(r"\b[\wÀ-ÿ']+\b", texto_normalizado)
        for palavra in palavras:
            melhor_match, melhor_score = None, 0
            for orig, corr in dicionario.items():
                score = fuzz.ratio(palavra.lower(), orig.lower())  # type: ignore[attr-defined]
                if score > melhor_score and score >= threshold:
                    melhor_match, melhor_score = corr, score
            if melhor_match and melhor_match != palavra:
                padrao = re.compile(rf"\b{re.escape(palavra)}\b", re.IGNORECASE)
                novo_texto, n = padrao.subn(melhor_match, texto_corrigido)
                if n > 0:
                    n_corrigidas += n
                texto_corrigido = novo_texto

    return texto_corrigido, n_corrigidas


class CacheDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        _ensure_dir(db_path.parent)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transcriptions (
              cache_key TEXT PRIMARY KEY,
              audio_hash TEXT NOT NULL,
              params_hash TEXT NOT NULL,
              orig_name TEXT NOT NULL,
              orig_ext TEXT NOT NULL,
              archived_path TEXT,
              created_at TEXT NOT NULL,
              meta_json TEXT NOT NULL,
              txt_content TEXT NOT NULL,
              json_content TEXT NOT NULL
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_audiohash ON transcriptions(audio_hash);")
        self.conn.commit()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT cache_key, audio_hash, params_hash, orig_name, orig_ext, archived_path, created_at, meta_json, txt_content, json_content "
            "FROM transcriptions WHERE cache_key=?",
            (cache_key,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "cache_key": row[0],
            "audio_hash": row[1],
            "params_hash": row[2],
            "orig_name": row[3],
            "orig_ext": row[4],
            "archived_path": row[5],
            "created_at": row[6],
            "meta": json.loads(row[7]),
            "txt": row[8],
            "json": json.loads(row[9]),
        }

    def upsert(
        self,
        cache_key: str,
        audio_hash: str,
        params_hash: str,
        orig_name: str,
        orig_ext: str,
        archived_path: Optional[str],
        meta: Dict[str, Any],
        txt_content: str,
        json_obj: Dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO transcriptions (
              cache_key, audio_hash, params_hash, orig_name, orig_ext, archived_path, created_at, meta_json, txt_content, json_content
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
              archived_path=excluded.archived_path,
              meta_json=excluded.meta_json,
              txt_content=excluded.txt_content,
              json_content=excluded.json_content;
            """,
            (
                cache_key,
                audio_hash,
                params_hash,
                orig_name,
                orig_ext,
                archived_path,
                _now_iso(),
                json.dumps(meta, ensure_ascii=False),
                txt_content,
                json.dumps(json_obj, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


@dataclass
class ASRParams:
    model: str
    language: str
    device: str
    compute_type: str
    vad_filter: bool
    beam_size: int


def _params_hash(params: ASRParams) -> str:
    payload = {
        "model": params.model,
        "language": params.language,
        "device": params.device,
        "compute_type": params.compute_type,
        "vad_filter": params.vad_filter,
        "beam_size": params.beam_size,
        "pipeline": "faster-whisper",
    }
    b = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(b)


def _run_asr_faster_whisper(audio_path: Path, params: ASRParams, errors: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as e:
        errors.append({"stage": "asr_import", "error": f"{type(e).__name__}: {e}"})
        return []

    try:
        model = WhisperModel(params.model, device=params.device, compute_type=params.compute_type)
    except Exception as e:
        errors.append({"stage": "asr_load_model", "error": f"{type(e).__name__}: {e}"})
        return []

    segments_out: List[Dict[str, Any]] = []
    hb_stop: Optional[threading.Event] = None
    hb_th: Optional[threading.Thread] = None

    try:
        hb_stop, hb_th = _start_heartbeat("ASR em execução", every_s=15.0)
        last_seg_log = time.time()

        seg_iter, _info = model.transcribe(
            str(audio_path),
            language=params.language,
            vad_filter=params.vad_filter,
            beam_size=params.beam_size,
        )

        for seg in seg_iter:
            now = time.time()
            if now - last_seg_log >= 60.0:
                print("  Progresso: ASR processando segmentos")
                last_seg_log = now

            text = (seg.text or "").strip()
            if not text:
                continue
            segments_out.append({"start": float(seg.start), "end": float(seg.end), "text": text})

    except Exception as e:
        errors.append({"stage": "asr_transcribe", "error": f"{type(e).__name__}: {e}"})
        return []
    finally:
        if hb_stop is not None and hb_th is not None:
            _stop_heartbeat(hb_stop, hb_th)

    return segments_out


def _load_pyannote_pipeline(hf_token: str, device: str, errors: List[Dict[str, str]]):
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except Exception as e:
        errors.append({"stage": "diar_import", "error": f"{type(e).__name__}: {e}"})
        return None

    model_id = "pyannote/speaker-diarization-3.1"
    variants = [{"token": hf_token}, {"hf_token": hf_token}, {"use_auth_token": hf_token}]

    last_exc: Optional[Exception] = None
    for kwargs in variants:
        try:
            pipe = Pipeline.from_pretrained(model_id, **kwargs)
            try:
                if hasattr(pipe, "to"):
                    pipe.to(device)
            except Exception:
                pass
            return pipe
        except TypeError as e:
            last_exc = e
            continue
        except Exception as e:
            last_exc = e
            break

    errors.append({"stage": "diar_load_pipeline", "error": f"{type(last_exc).__name__}: {last_exc}"})
    return None


def _preload_audio_no_torchcodec(audio_path: Path, errors: List[Dict[str, str]]):
    try:
        import soundfile as sf  # type: ignore
        import torch  # type: ignore

        data, sr = sf.read(str(audio_path), dtype="float32", always_2d=True)
        mono = data.mean(axis=1)
        waveform = torch.from_numpy(mono).unsqueeze(0)
        if waveform.dtype != torch.float32:
            waveform = waveform.to(torch.float32)
        return waveform, int(sr)
    except Exception as e_sf:
        errors.append({"stage": "diar_preload_sf", "error": f"{type(e_sf).__name__}: {e_sf}"})

    try:
        import wave
        import torch  # type: ignore

        if audio_path.suffix.lower() != ".wav":
            raise RuntimeError("fallback wave suporta apenas WAV PCM")

        with wave.open(str(audio_path), "rb") as wf:
            sr = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if sampwidth == 2:
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise RuntimeError(f"sampwidth não suportado no fallback wave: {sampwidth}")

        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)

        waveform = torch.from_numpy(audio).unsqueeze(0)
        if waveform.dtype != torch.float32:
            waveform = waveform.to(torch.float32)
        return waveform, int(sr)

    except Exception as e_w:
        errors.append({"stage": "diar_preload_wave", "error": f"{type(e_w).__name__}: {e_w}"})
        raise RuntimeError("preload_failed_no_torchcodec") from e_w


def _extract_annotation(diar_obj: Any, errors: List[Dict[str, str]]):
    try:
        if diar_obj is None:
            return None

        if hasattr(diar_obj, "itertracks"):
            return diar_obj

        if hasattr(diar_obj, "speaker_diarization"):
            ann = getattr(diar_obj, "speaker_diarization")
            if ann is not None and hasattr(ann, "itertracks"):
                return ann

        if hasattr(diar_obj, "exclusive_speaker_diarization"):
            ann = getattr(diar_obj, "exclusive_speaker_diarization")
            if ann is not None and hasattr(ann, "itertracks"):
                return ann

        if hasattr(diar_obj, "annotation"):
            ann = getattr(diar_obj, "annotation")
            if ann is not None and hasattr(ann, "itertracks"):
                return ann

        if isinstance(diar_obj, dict):
            for k in ("speaker_diarization", "exclusive_speaker_diarization", "annotation"):
                ann = diar_obj.get(k)
                if ann is not None and hasattr(ann, "itertracks"):
                    return ann

        errors.append({"stage": "diar_extract_annotation", "error": f"unsupported_diar_output_type={type(diar_obj).__name__}"})
        return None

    except Exception as e:
        errors.append({"stage": "diar_extract_annotation", "error": f"{type(e).__name__}: {e}"})
        return None


def _run_diarization_pyannote(audio_path: Path, hf_token: str, device: str, errors: List[Dict[str, str]]):
    pipe = _load_pyannote_pipeline(hf_token, device, errors)
    if pipe is None:
        return None, False, "pipeline_load_failed"

    hb_stop, hb_th = _start_heartbeat("Diarização em execução", every_s=15.0)

    try:
        try:
            waveform, sample_rate = _preload_audio_no_torchcodec(audio_path, errors)
        except Exception as e_pre:
            errors.append({"stage": "diar_preload", "error": f"{type(e_pre).__name__}: {e_pre}"})
            return None, False, "preload_failed"

        try:
            diar_raw = pipe({"waveform": waveform, "sample_rate": int(sample_rate)})
        except Exception as e_apply:
            errors.append({"stage": "diar_apply", "error": f"{type(e_apply).__name__}: {e_apply}"})
            return None, False, "pipeline_apply_failed"

        ann = _extract_annotation(diar_raw, errors)
        if ann is None:
            return None, False, "itertracks_failed"

        speakers = set()
        try:
            for _, _, lab in ann.itertracks(yield_label=True):
                speakers.add(str(lab))
        except Exception as e_it:
            errors.append({"stage": "diar_itertracks", "error": f"{type(e_it).__name__}: {e_it}"})
            return ann, False, "itertracks_failed"

        if len(speakers) < 2:
            return ann, False, "single_speaker"

        return ann, True, "ok"

    finally:
        _stop_heartbeat(hb_stop, hb_th)


def _assign_speakers_to_segments(asr_segments: List[Dict[str, Any]], ann) -> List[Dict[str, Any]]:
    turns: List[Tuple[float, float, str]] = []
    for segment, _, speaker in ann.itertracks(yield_label=True):
        turns.append((float(segment.start), float(segment.end), str(speaker)))

    def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
        return max(0.0, min(a1, b1) - max(a0, b0))

    def normalize_label(raw: str) -> str:
        r = (raw or "").strip()
        m = re.match(r"^SPEAKER_(\d{1,2})$", r, flags=re.IGNORECASE)
        if m:
            n = int(m.group(1))
            return f"SPEAKER_{n:02d}"
        m = re.search(r"(\d{1,2})$", r)
        if m:
            n = int(m.group(1))
            return f"SPEAKER_{n:02d}"
        return "SPEAKER_02"

    enriched: List[Dict[str, Any]] = []
    for seg in asr_segments:
        st = float(seg.get("start", 0.0))
        en = float(seg.get("end", st))

        best_spk = None
        best_ov = 0.0
        for ts, te, spk in turns:
            ov = overlap(st, en, ts, te)
            if ov > best_ov:
                best_ov = ov
                best_spk = spk

        seg2 = dict(seg)
        if best_spk is not None and best_ov > 0.0:
            seg2["speaker"] = normalize_label(best_spk)
        enriched.append(seg2)

    return enriched


def _speaker_to_role(speaker: str) -> str:
    if speaker == "SPEAKER_00":
        return "VENDEDOR"
    if speaker == "SPEAKER_01":
        return "CLIENTE"
    return "CLIENTE"


def _build_txt(segments: List[Dict[str, Any]], diarization_mode: str) -> str:
    lines: List[str] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue

        if diarization_mode != "pyannote":
            role = "VENDEDOR"
        else:
            speaker = str(seg.get("speaker") or "")
            role = _speaker_to_role(speaker)

        lines.append(f"[{role}] {text}")
    return "\n".join(lines) + ("\n" if lines else "")


def _write_text(path: Path, content: str) -> None:
    _ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _iter_audio_files(input_dir: Path, pattern: str, recursive: bool):
    if recursive:
        yield from input_dir.rglob(pattern)
    else:
        yield from input_dir.glob(pattern)


def resolve_audio_files(input_dir: Path, pattern: str, recursive: bool, only_file: str) -> List[Path]:
    input_dir = input_dir.resolve()
    if not input_dir.exists():
        return []

    if only_file:
        p = Path(only_file)
        if p.exists() and p.is_file():
            return [p.resolve()]

        p2 = (input_dir / only_file)
        if p2.exists() and p2.is_file():
            return [p2.resolve()]

        candidates = []
        for fp in _iter_audio_files(input_dir, pattern, recursive):
            if fp.is_file() and only_file.lower() in fp.name.lower():
                candidates.append(fp.resolve())
        candidates.sort()
        return candidates[:1]

    files: List[Path] = []
    for fp in _iter_audio_files(input_dir, pattern, recursive):
        if not fp.is_file():
            continue
        if fp.suffix.lower() in _AUDIO_EXTS:
            files.append(fp.resolve())
    files.sort()
    return files


def _archive_audio(audio_path: Path, cache_dir: Path, audio_hash: str) -> Optional[Path]:
    _ensure_dir(cache_dir)
    safe_name = _safe_filename(audio_path.stem)
    ext = audio_path.suffix.lower() or ".wav"
    dest = cache_dir / f"{audio_hash[:16]}__{safe_name}{ext}"

    if dest.exists():
        return dest.resolve()

    try:
        shutil.move(str(audio_path), str(dest))
        return dest.resolve()
    except Exception:
        try:
            shutil.copy2(str(audio_path), str(dest))
            return dest.resolve()
        except Exception:
            return None


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="01_transcricao.py — SPIN Analyzer — ASR local (faster-whisper) + diarização opcional (pyannote)"
    )

    ap.add_argument("--input_dir", default="arquivos_audio")
    ap.add_argument("--txt_dir", default="arquivos_transcritos/txt")
    ap.add_argument("--json_dir", default="arquivos_transcritos/json")

    ap.add_argument("--pattern", default="*.wav")
    ap.add_argument("--recursive", default="true")
    ap.add_argument("--only_file", default="")

    ap.add_argument("--model", default="medium")
    ap.add_argument("--language", default=DEFAULT_LANG)

    ap.add_argument("--device", default="auto")
    ap.add_argument("--beam_size", type=int, default=5)
    ap.add_argument("--vad_filter", default="true")

    ap.add_argument("--dict_path", default="assets/dicionario_televendas.txt")

    ap.add_argument("--force", action="store_true", help="Ignora cache e reprocessa o áudio")
    return ap


def main() -> int:
    t0 = time.time()
    args = build_argparser().parse_args()

    input_dir = Path(args.input_dir)
    txt_dir = Path(args.txt_dir)
    json_dir = Path(args.json_dir)

    _ensure_dir(txt_dir)
    _ensure_dir(json_dir)

    cache_dir = (Path.cwd() / CACHE_DIR_NAME).resolve()
    _ensure_dir(cache_dir)
    cache_db_path = cache_dir / CACHE_DB_NAME
    db = CacheDB(cache_db_path)

    recursive = _parse_bool(args.recursive)
    vad_filter = _parse_bool(args.vad_filter)

    audio_files = resolve_audio_files(input_dir, args.pattern, recursive, args.only_file)
    if not audio_files:
        print(f"Nenhum áudio encontrado. input_dir={input_dir} pattern={args.pattern} recursive={recursive} only_file={args.only_file!r}")
        db.close()
        return 2

    hf_token = (os.getenv("HF_TOKEN") or "").strip()
    hf_present = bool(hf_token)

    dicionario = carregar_dicionario(args.dict_path)
    dict_enabled = bool(dicionario)

    if dict_enabled and fuzz is None:
        print("Erro: fuzzywuzzy não está instalado, mas o dicionário existe.")
        print("Instale com: pip install fuzzywuzzy python-levenshtein")
        db.close()
        return 2

    resolved_device = _resolve_device(args.device)
    compute_type = "int8" if resolved_device == "cpu" else "float16"

    asr_params = ASRParams(
        model=str(args.model),
        language=str(args.language),
        device=resolved_device,
        compute_type=compute_type,
        vad_filter=bool(vad_filter),
        beam_size=int(args.beam_size),
    )
    params_hash = _params_hash(asr_params)

    print("SPIN Analyzer — 01_transcricao")
    print(f"Entrada: {input_dir.resolve()}")
    print(f"Saídas:  TXT={txt_dir.resolve()} | JSON={json_dir.resolve()}")
    print(f"Cache:   {cache_db_path}")
    print(f"ASR:     faster-whisper | model={asr_params.model} | device={asr_params.device} | compute_type={asr_params.compute_type} | lang={asr_params.language}")
    print(f"Diarização: {'habilitada' if hf_present else 'desabilitada'} (HF_TOKEN {'presente' if hf_present else 'ausente'})")
    print(f"Itens:   {len(audio_files)}")
    print("-" * 72)

    for idx, audio_path in enumerate(audio_files, start=1):
        item_t0 = time.time()
        name = audio_path.name

        out_txt = txt_dir / f"{audio_path.stem}.txt"
        out_json = json_dir / f"{audio_path.stem}.json"

        try:
            audio_hash = _sha256_file(audio_path)
        except Exception as e:
            audio_hash = ""
            print(f"[{idx}/{len(audio_files)}] {name} | Aviso: falha ao calcular hash. Motivo: {type(e).__name__}: {e}")

        cache_key = _sha256_bytes(f"{audio_hash}|{params_hash}".encode("utf-8")) if audio_hash else ""

        if (not args.force) and cache_key:
            cached = db.get(cache_key)
            if cached:
                try:
                    _write_text(out_txt, cached["txt"])
                    _write_json(out_json, cached["json"])
                    elapsed = time.time() - item_t0
                    print(f"[{idx}/{len(audio_files)}] {name} | Cache: HIT | Tempo: {_format_elapsed(elapsed)} | TXT/JSON regenerados")
                    continue
                except Exception as e:
                    print(f"[{idx}/{len(audio_files)}] {name} | Cache: HIT, mas falhou ao escrever saídas. Reprocessando. Motivo: {type(e).__name__}: {e}")

        errors: List[Dict[str, str]] = []
        duration_s = _try_get_wav_duration_seconds(audio_path)

        print(f"[{idx}/{len(audio_files)}] {name} | Início | Device={asr_params.device} | Modelo={asr_params.model}")
        tick0 = time.time()

        asr_segments = _run_asr_faster_whisper(audio_path, asr_params, errors)
        print(f"[{idx}/{len(audio_files)}] {name} | ASR finalizado | Tempo parcial {_format_elapsed(time.time() - tick0)} | Segmentos {len(asr_segments)}")

        if not asr_segments:
            diarization_mode = "fallback_all_vendor"
            segments_final: List[Dict[str, Any]] = []
            total_corrigidas = 0
        else:
            if _PUNCT_MODEL is not None:
                for seg in asr_segments:
                    try:
                        seg["text"] = _PUNCT_MODEL.restore_punctuation(seg.get("text", ""))
                    except Exception:
                        pass

            total_corrigidas = 0
            if dict_enabled:
                for seg in asr_segments:
                    try:
                        seg["text"], n_corr = aplicar_dicionario(seg.get("text", ""), dicionario)
                        total_corrigidas += int(n_corr)
                    except Exception:
                        pass

            diarization_mode = "fallback_all_vendor"
            segments_final = asr_segments

            if hf_present:
                ann, diar_ok, reason = _run_diarization_pyannote(audio_path, hf_token, asr_params.device, errors)

                # ==========================
                # AJUSTE: não jogar fora ann em single_speaker.
                # Tenta assign mesmo assim; se falhar, fallback.
                # ==========================
                if ann is not None:
                    try:
                        segments_try = _assign_speakers_to_segments(asr_segments, ann)
                        has_any_speaker = any(("speaker" in s and str(s.get("speaker")).strip()) for s in segments_try)
                        if has_any_speaker:
                            segments_final = segments_try
                            diarization_mode = "pyannote"
                        else:
                            diarization_mode = "fallback_all_vendor"
                    except Exception as e:
                        errors.append({"stage": "diar_assign", "error": f"{type(e).__name__}: {e}"})
                        diarization_mode = "fallback_all_vendor"

                if not diar_ok:
                    errors.append({"stage": "diar_quality", "error": f"diarization_not_reliable: {reason}"})

        print(f"[{idx}/{len(audio_files)}] {name} | Correções dicionário: {total_corrigidas}")

        meta: Dict[str, Any] = {
            "file": str(audio_path.resolve()),
            "file_name": audio_path.name,
            "duration_seconds": duration_s,
            "asr": {
                "engine": "faster-whisper",
                "model": asr_params.model,
                "language": asr_params.language,
                "device": asr_params.device,
                "compute_type": asr_params.compute_type,
                "vad_filter": asr_params.vad_filter,
                "beam_size": asr_params.beam_size,
            },
            "diarization": diarization_mode,
            "created_at": _now_iso(),
        }

        json_obj: Dict[str, Any] = {
            "metadata": meta,
            "diarization": diarization_mode,
            "errors": errors,
            "segments": segments_final,
        }

        txt_content = _build_txt(segments_final, diarization_mode)

        try:
            _write_text(out_txt, txt_content)
        except Exception as e:
            print(f"[{idx}/{len(audio_files)}] {name} | Erro ao salvar TXT: {type(e).__name__}: {e}")

        try:
            _write_json(out_json, json_obj)
        except Exception as e:
            print(f"[{idx}/{len(audio_files)}] {name} | Erro ao salvar JSON: {type(e).__name__}: {e}")

        archived_path = None
        if audio_hash:
            try:
                archived = _archive_audio(audio_path, cache_dir, audio_hash)
                archived_path = str(archived) if archived else None
            except Exception:
                archived_path = None

        if cache_key:
            try:
                meta_cache = dict(meta)
                meta_cache["archived_path"] = archived_path
                db.upsert(
                    cache_key=cache_key,
                    audio_hash=audio_hash,
                    params_hash=params_hash,
                    orig_name=audio_path.stem,
                    orig_ext=audio_path.suffix.lower(),
                    archived_path=archived_path,
                    meta=meta_cache,
                    txt_content=txt_content,
                    json_obj=json_obj,
                )
            except Exception as e:
                print(f"[{idx}/{len(audio_files)}] {name} | Aviso: falha ao salvar cache. Motivo: {type(e).__name__}: {e}")

        elapsed = time.time() - item_t0
        print(f"[{idx}/{len(audio_files)}] {name} | Diarização: {diarization_mode} | Erros: {len(errors)} | Tempo: {_format_elapsed(elapsed)} | Saídas: OK")

    total_elapsed = time.time() - t0
    print("-" * 72)
    print(f"Concluído. Itens: {len(audio_files)} | Tempo total: {_format_elapsed(total_elapsed)}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
