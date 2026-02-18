#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts_base/01_transcricao.py — SPIN Analyzer (LOCAL Windows) — WhisperX + Align + (Opcional) Pontuação + Dicionário Fuzzy + (Opcional) Diarização Pyannote 3.1

Dependências mínimas (instale no seu venv):
  pip install -U torch torchaudio whisperx numpy python-dotenv
  pip install -U fuzzywuzzy python-levenshtein
  pip install -U deepmultilingualpunctuation          (opcional, apenas se quiser pontuação)
  pip install -U pyannote.audio                       (necessário para diarização via pyannote no WhisperX quando HF_TOKEN existir)
Observações:
- Não usa nenhum serviço remoto, exceto o acesso ao Hugging Face quando HF_TOKEN estiver configurado (para baixar/usar o modelo pyannote).
- Lógica de transcrição segue EXATAMENTE o pipeline do Paulo (transcrever_pipeline_v2.py), apenas adaptando:
  - CLI completo
  - Defaults de pastas do projeto
  - Logs profissionais (sem emojis)
  - Comportamento com/sem HF_TOKEN conforme especificado
"""

import argparse
from pathlib import Path
import os
import re
import json
import time

import torch
import whisperx

# ===============================
# Pontuação (opcional)
# ===============================
try:
    from deepmultilingualpunctuation import PunctuationModel  # type: ignore
    _PUNCT_MODEL = PunctuationModel()
except Exception:
    _PUNCT_MODEL = None

# ===============================
# fuzzywuzzy (dicionário) — requerido quando o dicionário existir
# (se não estiver instalado, o script segue sem correções)
# ===============================
try:
    from fuzzywuzzy import fuzz  # type: ignore
except Exception:
    fuzz = None


# -------------------------------------------------------------
# Dicionário (estrutura idêntica ao do Paulo)
# -------------------------------------------------------------
def carregar_dicionario(dict_path: str) -> dict:
    """Carrega dicionário no formato 'termo_original = termo_corrigido'."""
    dicionario = {}
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
        print(f"Dicionario carregado: {len(dicionario)} entradas.")
    else:
        print("Dicionario nao encontrado. Seguindo sem correcoes lexicais.")
    return dicionario


def aplicar_dicionario(texto: str, dicionario: dict, threshold: int = 80):
    """Aplica o dicionário com suporte a bigrama e fuzzy (mesma estrutura do Paulo)."""
    texto_corrigido = texto
    n_corrigidas = 0

    # Normaliza pontuação (para fuzzy em palavras isoladas)
    texto_normalizado = re.sub(r"[^\w\sÀ-ÿ]", "", texto_corrigido)

    # Substituições exatas (bigrama e compostos)
    for orig, corr in sorted(dicionario.items(), key=lambda x: len(x[0]), reverse=True):
        padrao = re.compile(rf"\b{re.escape(orig)}\b", flags=re.IGNORECASE)
        novo_texto, n = padrao.subn(corr, texto_corrigido)
        if n > 0:
            n_corrigidas += n
        texto_corrigido = novo_texto

    # Fuzzy para palavras isoladas
    if fuzz is not None:
        palavras = re.findall(r"\b[\wÀ-ÿ']+\b", texto_normalizado)
        for palavra in palavras:
            melhor_match, melhor_score = None, 0
            for orig, corr in dicionario.items():
                score = fuzz.ratio(palavra.lower(), orig.lower())
                if score > melhor_score and score >= threshold:
                    melhor_match, melhor_score = corr, score
            if melhor_match and melhor_match != palavra:
                padrao = re.compile(rf"\b{re.escape(palavra)}\b", re.IGNORECASE)
                novo_texto, n = padrao.subn(melhor_match, texto_corrigido)
                if n > 0:
                    n_corrigidas += n
                texto_corrigido = novo_texto

    return texto_corrigido, n_corrigidas


# -------------------------------------------------------------
# Saídas (TXT e JSON)
# -------------------------------------------------------------
def save_txt(segments, out_path: Path, hf_token_present: bool):
    """
    Formato obrigatório do TXT:
      [VENDEDOR] ...
      [CLIENTE] ...

    Regras:
    - Com diarização (HF_TOKEN presente): SPEAKER_00 -> VENDEDOR, SPEAKER_01 -> CLIENTE, demais -> CLIENTE (padroniza TXT).
    - Sem diarização (HF_TOKEN ausente): tudo vira VENDEDOR (para nao perder falas do vendedor e nao quebrar o 02).
    """
    with open(out_path, "w", encoding="utf-8") as f:
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            text = (seg.get("text") or "").strip()
            if not text:
                continue

            if not hf_token_present:
                label = "VENDEDOR"
            else:
                speaker = seg.get("speaker", "UNK")
                if speaker == "SPEAKER_00":
                    label = "VENDEDOR"
                elif speaker == "SPEAKER_01":
                    label = "CLIENTE"
                else:
                    label = "CLIENTE"

            f.write(f"[{label}] {text}\n")


def save_json(segments, out_path: Path):
    """
    Salva JSON por arquivo.
    Mantem a mesma ideia do Paulo: JSON como lista de segmentos (dicts) do WhisperX.
    """
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)


# -------------------------------------------------------------
# Descoberta de arquivos (pattern + recursive + only_file)
# -------------------------------------------------------------
_AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".mp4"}


def _iter_audio_files(input_dir: Path, pattern: str, recursive: bool):
    if recursive:
        yield from input_dir.rglob(pattern)
    else:
        yield from input_dir.glob(pattern)


def resolve_audio_files(input_dir: Path, pattern: str, recursive: bool, only_file: str):
    input_dir = input_dir.resolve()
    if not input_dir.exists():
        return []

    # only_file pode ser caminho absoluto/relativo, ou nome parcial
    if only_file:
        p = Path(only_file)
        if p.exists() and p.is_file():
            return [p.resolve()]

        p2 = (input_dir / only_file)
        if p2.exists() and p2.is_file():
            return [p2.resolve()]

        # match parcial por nome (sem exigir ext)
        candidates = []
        for fp in _iter_audio_files(input_dir, pattern, recursive):
            if fp.is_file() and only_file.lower() in fp.name.lower():
                candidates.append(fp.resolve())
        candidates.sort()
        return candidates[:1]

    files = []
    for fp in _iter_audio_files(input_dir, pattern, recursive):
        if not fp.is_file():
            continue
        if fp.suffix.lower() in _AUDIO_EXTS:
            files.append(fp.resolve())
    files.sort()
    return files


# -------------------------------------------------------------
# Main — pipeline do Paulo, com adaptações de paths/CLI/logs
# -------------------------------------------------------------
def build_argparser():
    ap = argparse.ArgumentParser(description="01_transcricao.py — SPIN Analyzer — WhisperX local")

    ap.add_argument("--input_dir", default="arquivos_audio")
    ap.add_argument("--txt_dir", default="arquivos_transcritos/txt")
    ap.add_argument("--json_dir", default="arquivos_transcritos/json")
    ap.add_argument("--dict_path", default="assets/dicionario_televendas.txt")

    ap.add_argument("--model", default="medium")
    ap.add_argument("--language", default="pt")

    ap.add_argument("--pattern", default="*.wav")
    ap.add_argument("--recursive", default="true")  # string para aceitar true/false
    ap.add_argument("--only_file", default="")

    return ap


def _parse_bool(s: str) -> bool:
    return str(s).strip().lower() in {"1", "true", "t", "yes", "y", "sim"}


def main():
    inicio_total = time.time()
    args = build_argparser().parse_args()

    in_dir = Path(args.input_dir)
    txt_dir = Path(args.txt_dir)
    json_dir = Path(args.json_dir)
    txt_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    # Device: GPU primeiro
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {device}")

    # HF_TOKEN: presente/ausente (log curto)
    hf_token = os.getenv("HF_TOKEN") or ""
    hf_present = bool(hf_token.strip())
    if hf_present:
        print("HF_TOKEN: presente (diarizacao ativa).")
    else:
        print("HF_TOKEN: ausente (sem diarizacao; TXT sai todo como VENDEDOR).")

    # Carregar dicionário (se existir)
    dicionario = carregar_dicionario(args.dict_path)
    if dicionario and fuzz is None:
        print("Aviso: fuzzywuzzy nao esta instalado; correcoes fuzzy serao ignoradas (somente substituicoes exatas).")

    # Carregar modelo WhisperX (mesma regra do Paulo)
    print("Carregando modelo WhisperX...")
    compute_type = "int8" if device == "cpu" else "float16"
    model = whisperx.load_model(args.model, device=device, compute_type=compute_type)

    # Arquivos
    recursive = _parse_bool(args.recursive)
    audio_files = resolve_audio_files(in_dir, args.pattern, recursive, args.only_file)
    if not audio_files:
        print(f"Nenhum audio encontrado em: {in_dir} | pattern={args.pattern} | recursive={recursive} | only_file={args.only_file!r}")
        return 2

    for audio_file in audio_files:
        print(f"\nArquivo: {audio_file.name}")
        inicio_audio = time.time()

        audio = whisperx.load_audio(str(audio_file))

        # ===== Transcrição =====
        result = model.transcribe(audio, batch_size=16, language=args.language)
        segments = result.get("segments", [])

        # ===== Alinhamento =====
        try:
            align_model, metadata = whisperx.load_align_model(language_code="pt", device=device)
            result_aligned = whisperx.align(segments, align_model, metadata, audio, device)
        except Exception as e:
            print(f"Alinhamento falhou. Usando segmentos originais. Motivo: {e}")
            result_aligned = {"segments": segments}

        # ===== Pontuação (opcional) =====
        if _PUNCT_MODEL:
            for seg in result_aligned.get("segments", []):
                try:
                    seg["text"] = _PUNCT_MODEL.restore_punctuation(seg.get("text", ""))
                except Exception:
                    pass

        # ===== Aplicar Dicionário =====
        total_corrigidas = 0
        if dicionario:
            for seg in result_aligned.get("segments", []):
                txt = seg.get("text", "")
                txt2, n_corr = aplicar_dicionario(txt, dicionario)
                seg["text"] = txt2
                total_corrigidas += int(n_corr)

        # ===== Diarização Moderna (somente se HF_TOKEN existir) =====
        if hf_present:
            try:
                from whisperx.diarize import DiarizationPipeline

                diarize_model = DiarizationPipeline(
                    model_name="pyannote/speaker-diarization-3.1",
                    use_auth_token=hf_token,
                    device=device,
                )
                diarize_segments = diarize_model(audio)
                result_aligned = whisperx.assign_word_speakers(diarize_segments, result_aligned)
                segments_final = result_aligned.get("segments", [])
                # Mantem o speaker no JSON como SPEAKER_XX (padrao do WhisperX)
                # O TXT fara o mapeamento para VENDEDOR/CLIENTE conforme regra.
            except Exception as e:
                print(f"Aviso: diarizacao falhou. Seguindo sem diarizacao. Motivo: {e}")
                segments_final = result_aligned.get("segments", [])
                hf_present_effective = False
            else:
                hf_present_effective = True
        else:
            segments_final = result_aligned.get("segments", [])
            hf_present_effective = False

        # ===== Salvar Saídas =====
        out_txt = txt_dir / f"{audio_file.stem}.txt"
        out_json = json_dir / f"{audio_file.stem}.json"

        save_txt(segments_final, out_txt, hf_present_effective)
        save_json(segments_final, out_json)

        duracao = time.time() - inicio_audio
        print(f"Tempo: {duracao:.1f}s | Correcoes: {total_corrigidas} | Saida TXT: {out_txt.name} | Saida JSON: {out_json.name}")

    tempo_total = time.time() - inicio_total
    print(f"\nConcluido. Tempo total: {tempo_total/60:.2f} minutos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
