# ==============================================================
# 01_transcricao.py
# Projeto: Tele_IA Transcrição (Cloud + Local)
# Saída COMPATÍVEL com 02_zeroshot.py
#
# ✅ Funciona:
# - Local (Windows/Linux) rodando o 01 normalmente
# - Streamlit Cloud (desde que as libs estejam no ambiente)
#
# ✅ Diarização:
# - --enable_diarization usa pyannote via whisperx (precisa token HF)
# - Sem token / falha → fallback automático (sem diarização, mas transcreve)
#
# 🔑 Token Hugging Face (para diarização pyannote):
# - use variável: HUGGINGFACE_TOKEN ou HF_TOKEN
# - Local: .env  -> HUGGINGFACE_TOKEN=hf_xxx
# - Streamlit Cloud: Secrets -> HUGGINGFACE_TOKEN="hf_xxx"
# ==============================================================

import argparse
import json
import os
import re
import time
import typing
from pathlib import Path

from dotenv import load_dotenv

# torch/whisperx podem ser pesados, mas são necessários
import torch
import whisperx

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# ==============================================================
# PyTorch safe globals (evita erro ao carregar alguns checkpoints)
# (mantém compat com setups mais novos)
# ==============================================================
try:
    from omegaconf.listconfig import ListConfig
    from omegaconf.dictconfig import DictConfig
    from omegaconf.base import ContainerMetadata

    torch.serialization.add_safe_globals(
        [ListConfig, DictConfig, ContainerMetadata, typing.Any]
    )
except Exception:
    # se omegaconf não estiver instalado, seguimos
    pass

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
# Inicializações
# ==============================================================
load_dotenv()


# ==============================================================
# Util: token HF
# ==============================================================
def get_hf_token() -> str | None:
    t = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN") or os.getenv(
        "HUGGINGFACEHUB_API_TOKEN"
    )
    if t:
        t = t.strip()
    return t or None


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
# Heurísticas de papel (cliente/vendedor) - melhores do que só "primeira fala"
# ==============================================================
CLIENTE_MARKERS = [
    "tudo bem",
    "ok",
    "sim",
    "claro",
    "pode",
    "aham",
    "uhum",
    "obrigado",
    "obrigada",
    "beleza",
    "certo",
    "perfeito",
    "tá",
    "tá bom",
    "entendi",
    "quanto",
    "preço",
    "valor",
    "fica quanto",
    "me manda",
    "pode ser",
    "vou ver",
]

VENDEDOR_MARKERS = [
    "aqui é",
    "sou da",
    "estou ligando",
    "estou entrando em contato",
    "nossa empresa",
    "posso falar",
    "falo com",
    "bom dia",
    "boa tarde",
    "boa noite",
    "como posso ajudar",
    "pra gente",
    "nosso",
    "nós",
    "vou te explicar",
    "funciona assim",
    "plano",
    "proposta",
    "condições",
]


# ==============================================================
# Limpeza e quebra
# ==============================================================
def _limpar_texto(t: str) -> str:
    t = (t or "").strip()
    t = re.sub(r"\s+", " ", t).strip()
    # remove rótulos comuns
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
        "Tudo bem",
        "Tudo ótimo",
        "Claro",
        "Perfeito",
        "Ótimo",
        "Sim",
        "Ok",
        "Aham",
        "Uhum",
        "Obrigado",
        "Obrigada",
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


def _segmentos_para_linhas(segments):
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
# Mapeamento diarização -> VENDEDOR/CLIENTE (mais preciso)
# ==============================================================
def _score_markers(texto: str, markers: list[str]) -> int:
    t = (texto or "").lower()
    score = 0
    for m in markers:
        if m in t:
            score += 1
    return score


def _mapear_speakers_para_papeis(segments_with_speakers):
    """
    Recebe segments com keys: text, speaker (ex: 'SPEAKER_00')
    Retorna dict { 'SPEAKER_00': 'VENDEDOR', 'SPEAKER_01': 'CLIENTE', ... }
    Heurística:
      1) Quem fala primeiro tende a ser VENDEDOR (em ligações de venda).
      2) Somatório de marcadores por speaker decide.
      3) Se empatar, usa primeira fala.
    """
    speakers = {}
    order = []
    for seg in segments_with_speakers:
        sp = seg.get("speaker") or "SPEAKER_00"
        if sp not in speakers:
            speakers[sp] = {"vend": 0, "cli": 0, "n": 0}
            order.append(sp)
        txt = seg.get("text", "")
        speakers[sp]["vend"] += _score_markers(txt, VENDEDOR_MARKERS)
        speakers[sp]["cli"] += _score_markers(txt, CLIENTE_MARKERS)
        speakers[sp]["n"] += 1

    if not speakers:
        return {}

    # speaker principal (mais falas)
    sp_main = max(speakers.keys(), key=lambda k: speakers[k]["n"])

    # decide vendedor: maior (vend-cli); empate -> quem falou primeiro
    def vend_score(sp):
        return speakers[sp]["vend"] - speakers[sp]["cli"]

    best = sorted(speakers.keys(), key=lambda sp: (vend_score(sp), -order.index(sp)))
    sp_vendedor = best[-1]  # maior score

    # fallback: se tudo zero, primeira fala = vendedor
    if all(vend_score(sp) == 0 for sp in speakers.keys()):
        sp_vendedor = order[0]

    mapping = {}
    mapping[sp_vendedor] = "VENDEDOR"
    for sp in speakers.keys():
        if sp != sp_vendedor:
            mapping[sp] = "CLIENTE"

    # se só tem 1 speaker, ainda assim marca como VENDEDOR (e pronto)
    if len(mapping) == 1:
        mapping[sp_main] = "VENDEDOR"

    return mapping


# ==============================================================
# Classificação final em linhas (sem diarização)
# ==============================================================
def classificar_turnos_simples(linhas):
    """
    REGRA:
    - Primeira fala = VENDEDOR
    - Cliente detectado → CLIENTE
    - Vendedor detectado → VENDEDOR
    - Dúvida → VENDEDOR (intencional)
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for linha in linhas:
            f.write(linha.strip() + "\n")


def save_json(data, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==============================================================
# MAIN
# ==============================================================
def main():
    print("PIPELINE DE TRANSCRIÇÃO (CLOUD + LOCAL)")
    inicio_total = time.time()

    parser = argparse.ArgumentParser(description="WhisperX p/ SPIN (compat 02_zeroshot)")

    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--dict_path", required=False)
    parser.add_argument("--model", default="small")  # small/base/medium...
    parser.add_argument("--language", default="pt")
    parser.add_argument("--batch_size", type=int, default=8)

    # ✅ diarização
    parser.add_argument("--enable_diarization", action="store_true")
    parser.add_argument(
        "--diarize_min_speakers", type=int, default=2, help="mínimo speakers (pyannote)"
    )
    parser.add_argument(
        "--diarize_max_speakers", type=int, default=2, help="máximo speakers (pyannote)"
    )

    # ✅ alinhamento (opcional, pode ser pesado)
    parser.add_argument("--enable_align", action="store_true")

    # ✅ VAD (silero = mais estável; pyannote = avançado)
    parser.add_argument(
        "--vad",
        choices=["silero", "pyannote"],
        default="silero",
        help="VAD: silero (estável) / pyannote (avançado)",
    )

    args = parser.parse_args()

    BASE_DIR = Path(__file__).resolve().parent
    ROOT_DIR = BASE_DIR.parent  # mantém padrão do seu projeto

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

    print(f"[OK] {len(arquivos)} arquivos WAV encontrados em {input_dir}")

    dicionario = {}
    if args.dict_path:
        dicionario = carregar_dicionario(args.dict_path)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Dispositivo: {device}")

    compute_type = "int8" if device == "cpu" else "float16"

    # -----------------------------
    # 1) Load model (whisperx)
    # -----------------------------
    model = whisperx.load_model(
        args.model,
        device=device,
        compute_type=compute_type,
        vad_method=args.vad,  # evita cair em pyannote sem querer
        language=args.language,
    )

    hf_token = get_hf_token()
    if args.enable_diarization:
        if hf_token:
            print("[OK] Token Hugging Face detectado (diarização habilitada).")
        else:
            print(
                "[AVISO] --enable_diarization foi pedido, mas NÃO há token HF.\n"
                "        Defina HUGGINGFACE_TOKEN (ou HF_TOKEN) para diarização pyannote.\n"
                "        Vou fazer fallback automático (sem diarização)."
            )

    # -----------------------------
    # Process files
    # -----------------------------
    for audio_file in arquivos:
        print(f"\nProcessando: {audio_file.name}")
        inicio_audio = time.time()

        audio = whisperx.load_audio(str(audio_file))

        result = model.transcribe(
            audio, batch_size=args.batch_size, language=args.language
        )
        segments = result.get("segments", [])

        # aplica dicionário no texto bruto dos segments
        total_corrigidas = 0
        if dicionario:
            for seg in segments:
                txt2, n = aplicar_dicionario(seg.get("text", ""), dicionario)
                seg["text"] = txt2
                total_corrigidas += n

        # -----------------------------
        # 2) Align (opcional)
        # -----------------------------
        aligned_segments = segments
        align_data = None
        if args.enable_align and segments:
            try:
                print("[INFO] Alinhando (enable_align)...")
                align_model, metadata = whisperx.load_align_model(
                    language_code=args.language, device=device
                )
                align_data = whisperx.align(
                    segments,
                    align_model,
                    metadata,
                    audio,
                    device,
                    return_char_alignments=False,
                )
                aligned_segments = align_data.get("segments", segments)
                print("[OK] Align concluído.")
            except Exception as e:
                print(f"[AVISO] Align falhou, seguindo sem align. Motivo: {e}")
                aligned_segments = segments

        # -----------------------------
        # 3) Diarização (opcional)
        # -----------------------------
        final_lines = []
        diarization_used = False
        diarization_error = None
        segments_with_speakers = None

        if args.enable_diarization and hf_token:
            try:
                # Import tardio: evita quebrar o script se pyannote/torchaudio tiverem treta
                print("[INFO] Rodando diarização (pyannote via whisperx)...")
                diarize_pipeline = whisperx.DiarizationPipeline(
                    use_auth_token=hf_token, device=device
                )
                diarize_segments = diarize_pipeline(
                    audio,
                    min_speakers=args.diarize_min_speakers,
                    max_speakers=args.diarize_max_speakers,
                )

                # atribui speakers aos segments (usa os alinhados se existirem)
                segments_with_speakers = whisperx.assign_word_speakers(
                    diarize_segments, {"segments": aligned_segments}
                ).get("segments", aligned_segments)

                diarization_used = True
                print("[OK] Diarização concluída.")

                # Mapear SPEAKER_xx -> VENDEDOR/CLIENTE (mais preciso)
                mapping = _mapear_speakers_para_papeis(segments_with_speakers)

                # Gerar linhas finais com papel (V/C) por segment
                for seg in segments_with_speakers:
                    sp = seg.get("speaker") or "SPEAKER_00"
                    papel = mapping.get(sp, "VENDEDOR")
                    txt = _limpar_texto(seg.get("text", ""))
                    if not txt:
                        continue
                    for frase in _split_por_pontuacao(txt):
                        for pedaco in _split_por_markers(frase):
                            p = _limpar_texto(pedaco)
                            if p:
                                final_lines.append(f"[{papel}] {p}")

                # remove duplicatas consecutivas
                dedup = []
                last = None
                for l in final_lines:
                    if l != last:
                        dedup.append(l)
                    last = l
                final_lines = dedup

            except Exception as e:
                diarization_error = str(e)
                diarization_used = False
                print(
                    "[AVISO] Diarização falhou. Vou seguir com fallback (sem diarização).\n"
                    f"        Motivo: {diarization_error}"
                )

        # -----------------------------
        # 4) Fallback sem diarização
        # -----------------------------
        if not diarization_used:
            linhas_raw = _segmentos_para_linhas(aligned_segments)
            final_lines = classificar_turnos_simples(linhas_raw)

        # -----------------------------
        # Save
        # -----------------------------
        out_txt = TXT_DIR / f"{audio_file.stem}.txt"
        out_json = JSON_DIR / f"{audio_file.stem}.json"

        payload = {
            "file": audio_file.name,
            "device": device,
            "model": args.model,
            "language": args.language,
            "vad": args.vad,
            "enable_align": bool(args.enable_align),
            "enable_diarization": bool(args.enable_diarization),
            "diarization_used": bool(diarization_used),
            "diarization_error": diarization_error,
            "correcoes_dicionario": int(total_corrigidas),
            "segments": segments_with_speakers if diarization_used else aligned_segments,
            "linhas": final_lines,
        }

        save_txt(final_lines, out_txt)
        save_json(payload, out_json)

        print(
            f"[OK] Correções: {total_corrigidas} | Tempo: {time.time() - inicio_audio:.1f}s"
        )
        print(f"[TXT]  {out_txt}")
        print(f"[JSON] {out_json}")

    print(f"\nFINALIZADO em {(time.time() - inicio_total)/60:.2f} minutos")
    print(f"[PASTA TXT]  {TXT_DIR}")
    print(f"[PASTA JSON] {JSON_DIR}")


if __name__ == "__main__":
    main()
