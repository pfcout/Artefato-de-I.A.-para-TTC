# ==============================================================
# 01_transcricao.py
# Projeto: Tele_IA Transcrição - Versão Estável Windows
# Saída COMPATÍVEL com 02_zeroshot.py
# ==============================================================
import argparse
from pathlib import Path
import re
import json
import time
import typing

import torch
import torchaudio  # só para garantir backend/compat (não precisa usar direto)
import whisperx
from dotenv import load_dotenv

from omegaconf.listconfig import ListConfig
from omegaconf.dictconfig import DictConfig
from omegaconf.base import ContainerMetadata

# ==============================================================
# PyTorch >= 2.6: allowlist para checkpoints que usam OmegaConf etc.
# (necessário principalmente quando usar Pyannote)
# ==============================================================
torch.serialization.add_safe_globals([
    ListConfig,
    DictConfig,
    ContainerMetadata,
    typing.Any,
])

# ==============================================================
# Inicializações
# ==============================================================
load_dotenv()

# ==============================================================
# fuzzywuzzy (dicionário opcional)
# ==============================================================
try:
    from fuzzywuzzy import fuzz
except ImportError:
    raise ImportError(
        "Biblioteca 'fuzzywuzzy' não encontrada.\n"
        "Instale com: pip install fuzzywuzzy python-levenshtein"
    )

# ==============================================================
# Dicionário (opcional)
# ==============================================================
def carregar_dicionario(dict_path: str) -> dict:
    dicionario = {}
    path = Path(dict_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    dicionario[k.strip()] = v.strip()
        print(f"[OK] Dicionário carregado: {len(dicionario)} entradas.")
    else:
        print("[INFO] Nenhum dicionário encontrado.")
    return dicionario


def aplicar_dicionario(texto: str, dicionario: dict, threshold: int = 80):
    texto_corrigido = texto
    n_corrigidas = 0

    texto_normalizado = re.sub(r"[^\w\sÀ-ÿ]", "", texto_corrigido)

    # Correções diretas
    for orig, corr in sorted(dicionario.items(), key=lambda x: len(x[0]), reverse=True):
        padrao = re.compile(rf"\b{re.escape(orig)}\b", flags=re.IGNORECASE)
        texto_corrigido, n = padrao.subn(corr, texto_corrigido)
        n_corrigidas += n

    # Correções fuzzy
    palavras = re.findall(r"\b[\wÀ-ÿ']+\b", texto_normalizado)
    for palavra in palavras:
        melhor_match, melhor_score = None, 0
        for orig, corr in dicionario.items():
            score = fuzz.ratio(palavra.lower(), orig.lower())
            if score >= threshold and score > melhor_score:
                melhor_match, melhor_score = corr, score

        if melhor_match and melhor_match.lower() != palavra.lower():
            padrao = re.compile(rf"\b{re.escape(palavra)}\b", re.IGNORECASE)
            texto_corrigido, n = padrao.subn(melhor_match, texto_corrigido)
            n_corrigidas += n

    return texto_corrigido, n_corrigidas


# ==============================================================
# Heurísticas simples de papel (INTENCIONALMENTE AGRESSIVAS)
# ==============================================================
CLIENTE_MARKERS = [
    "tudo bem", "ok", "sim", "claro", "pode", "aham", "uhum",
    "obrigado", "obrigada", "beleza", "certo", "perfeito", "tá"
]

VENDEDOR_MARKERS = [
    "aqui é", "sou da", "estou ligando", "estou entrando em contato",
    "nossa empresa", "posso falar", "falo com", "bom dia", "boa tarde"
]


# ==============================================================
# Limpeza e quebra de texto
# ==============================================================
def _limpar_texto(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^\[SPEAKER_\d+\]\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\[UNK\]\s*", "", t, flags=re.IGNORECASE)
    return t


def _split_por_pontuacao(texto: str):
    texto = _limpar_texto(texto)
    if not texto:
        return []
    partes = re.split(r"(?<=[\.\?\!])\s+", texto)
    return [p.strip() for p in partes if p.strip()]


def _split_por_markers(frase: str):
    if len(frase) <= 120:
        return [frase]

    marcadores = [
        "Tudo bem", "Tudo ótimo", "Claro", "Perfeito", "Ótimo",
        "Sim", "Ok", "Aham", "Uhum", "Obrigado", "Obrigada"
    ]

    f = frase
    for m in marcadores:
        f = re.sub(rf"(?<!^)\s+({re.escape(m)})\b", r" ||| \1", f)

    partes = [p.strip() for p in f.split("|||") if p.strip()]

    finais = []
    for p in partes:
        if len(p) > 220 and "," in p:
            finais.extend([x.strip() for x in p.split(",") if x.strip()])
        else:
            finais.append(p)

    return finais


def gerar_linhas_turnos(segments):
    linhas = []
    for seg in segments:
        txt = seg.get("text", "")
        for frase in _split_por_pontuacao(txt):
            for pedaco in _split_por_markers(frase):
                p = _limpar_texto(pedaco)
                if p:
                    linhas.append(p)

    # remove duplicatas consecutivas
    limpas, last = [], None
    for l in linhas:
        if l != last:
            limpas.append(l)
        last = l

    return limpas


# ==============================================================
# Classificação FINAL de turnos (REGRA DE OURO)
# ==============================================================
def classificar_turnos_simples(linhas):
    """
    REGRA:
    - Primeira fala = VENDEDOR
    - Cliente detectado → CLIENTE
    - Dúvida → VENDEDOR (INTENCIONAL)
    """
    saida = []

    for i, texto in enumerate(linhas):
        t = texto.lower()

        if i == 0:
            speaker = "VENDEDOR"
        elif any(c in t for c in CLIENTE_MARKERS):
            speaker = "CLIENTE"
        elif any(v in t for v in VENDEDOR_MARKERS):
            speaker = "VENDEDOR"
        else:
            speaker = "VENDEDOR"

        saida.append(f"[{speaker}] {texto}")

    return saida


# ==============================================================
# Saídas
# ==============================================================
def save_txt(linhas, out_path: Path):
    with open(out_path, "w", encoding="utf-8") as f:
        for linha in linhas:
            f.write(linha.strip() + "\n")


def save_json(data, out_path: Path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==============================================================
# MAIN
# ==============================================================
def main():
    print("PIPELINE DE TRANSCRIÇÃO (SAFE MODE WINDOWS)")
    inicio_total = time.time()

    parser = argparse.ArgumentParser(description="WhisperX estável p/ SPIN")

    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--dict_path", required=False)
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--enable_diarization", action="store_true")
    parser.add_argument("--enable_align", action="store_true")

    # ✅ NOVO: escolha de VAD (silero padrão para evitar Pyannote quebrando)
    parser.add_argument(
        "--vad",
        choices=["silero", "pyannote"],
        default="silero",
        help="Método de VAD (silero é o padrão estável; pyannote é modo avançado)"
    )

    args = parser.parse_args()

    BASE_DIR = Path(__file__).resolve().parent
    ROOT_DIR = BASE_DIR.parent

    TXT_DIR = ROOT_DIR / "arquivos_transcritos" / "txt"
    JSON_DIR = ROOT_DIR / "arquivos_transcritos" / "json"
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = ROOT_DIR / input_dir

    arquivos = list(input_dir.glob("*.wav"))
    if not arquivos:
        raise RuntimeError(f"Nenhum WAV encontrado em: {input_dir}")

    print(f"[OK] {len(arquivos)} arquivos WAV encontrados")

    dicionario = {}
    if args.dict_path:
        dicionario = carregar_dicionario(args.dict_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Dispositivo: {device}")

    # ✅ whisperx: passa VAD explicitamente para não cair em pyannote à toa
    model = whisperx.load_model(
        args.model,
        device=device,
        compute_type="int8" if device == "cpu" else "float16",
        vad_method=args.vad,
        language=args.language,  # evita "No language specified"
    )

    for audio_file in arquivos:
        print(f"\nProcessando: {audio_file.name}")
        inicio_audio = time.time()

        audio = whisperx.load_audio(str(audio_file))

        # ✅ mantém language no transcribe também (consistência)
        result = model.transcribe(audio, batch_size=8, language=args.language)
        segments = result.get("segments", [])

        # dicionário
        total_corrigidas = 0
        if dicionario:
            for seg in segments:
                txt2, n = aplicar_dicionario(seg.get("text", ""), dicionario)
                seg["text"] = txt2
                total_corrigidas += n

        linhas_raw = gerar_linhas_turnos(segments)
        linhas = classificar_turnos_simples(linhas_raw)

        out_txt = TXT_DIR / f"{audio_file.stem}.txt"
        out_json = JSON_DIR / f"{audio_file.stem}.json"

        save_txt(linhas, out_txt)
        save_json({"segments": segments, "linhas": linhas}, out_json)

        print(f"[OK] Correções: {total_corrigidas} | Tempo: {time.time() - inicio_audio:.1f}s")
        print(f"[TXT] {out_txt}")

    print(f"\nFINALIZADO em {(time.time() - inicio_total)/60:.2f} minutos")
    print(f"[PASTA TXT]  {TXT_DIR}")
    print(f"[PASTA JSON] {JSON_DIR}")


if __name__ == "__main__":
    main()
