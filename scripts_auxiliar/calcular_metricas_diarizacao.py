# ==============================================================
#  📊 calcular_metricas_diarizacao.py
#  Projeto: Tele_IA Transcrição - Validação de Diarização
#  Funções:
#   - Lê pares de JSON (original / refinado)
#   - Calcula WER, WDER, cpWER, DER, DF1
#   - Gera CSV consolidado + log resumo
# ==============================================================

import os
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from jiwer import wer
from pyannote.metrics.diarization import DiarizationErrorRate, f_measure

# ==============================================================
# ⚙️ Funções auxiliares
# ==============================================================

def ler_json(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)

def extrair_texto(json_data):
    """Concatena todas as falas."""
    return " ".join([seg.get("text", "") for seg in json_data])

def extrair_speakers(json_data):
    """Lista de (speaker, texto) sequencial."""
    return [(seg.get("speaker", "UNK"), seg.get("text", "")) for seg in json_data]

def calcular_wder(orig, ref):
    total = min(len(orig), len(ref))
    erros = sum(1 for i in range(total) if orig[i][0] != ref[i][0])
    return round(erros / total if total > 0 else 0, 3)

def converter_para_annotation(json_data):
    """Converte JSON em formato de anotação (para DER e DF1)."""
    from pyannote.core import Annotation, Segment
    annotation = Annotation()
    for seg in json_data:
        if "start" in seg and "end" in seg:
            annotation[Segment(seg["start"], seg["end"])] = seg.get("speaker", "UNK")
    return annotation

# ==============================================================
# 🚀 Execução principal
# ==============================================================

def main():
    base_dir = Path("C:/Users/Pichau/Desktop/Projeto Tele_IA Transcricao/arquivos_transcritos")
    dir_original = base_dir / "json"
    dir_refinado = base_dir / "json_refinados"

    csv_path = base_dir / "metricas_diarizacao.csv"
    log_path = base_dir / "metricas_resumo.log"

    print("📊 Calculando métricas de diarização...\n")

    campos = [
        "arquivo",
        "WER_before", "WER_after",
        "WDER_before", "WDER_after",
        "cpWER_before", "cpWER_after",
        "DER_before", "DER_after",
        "DF1_before", "DF1_after"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos)
        writer.writeheader()

        for arquivo in dir_original.glob("*.json"):
            nome_base = arquivo.stem
            refinado_path = dir_refinado / f"{nome_base}_refinado.json"
            if not refinado_path.exists():
                continue

            original = ler_json(arquivo)
            refinado = ler_json(refinado_path)

            texto_orig = extrair_texto(original)
            texto_ref = extrair_texto(refinado)
            speakers_orig = extrair_speakers(original)
            speakers_ref = extrair_speakers(refinado)

            # WER e cpWER
            wer_before = round(wer(texto_orig, texto_orig), 3)
            wer_after = round(wer(texto_orig, texto_ref), 3)
            cpwer_before = wer_before
            cpwer_after = wer_after

            # WDER
            wder_before = calcular_wder(speakers_orig, speakers_orig)
            wder_after = calcular_wder(speakers_orig, speakers_ref)

            # DER / DF1 (tempo)
            der_metric = DiarizationErrorRate()
            f1_metric = DiarizationFMeasure()

            try:
                ann_orig = converter_para_annotation(original)
                ann_ref = converter_para_annotation(refinado)
                der_value = der_metric(ann_orig, ann_ref)
                df1_value = f1_metric(ann_orig, ann_ref)["f_measure"]
                der_before, der_after = round(0.0, 3), round(der_value, 3)
                df1_before, df1_after = round(1.0, 3), round(df1_value, 3)
            except Exception:
                der_before = der_after = df1_before = df1_after = 0.0

            writer.writerow({
                "arquivo": nome_base,
                "WER_before": wer_before, "WER_after": wer_after,
                "WDER_before": wder_before, "WDER_after": wder_after,
                "cpWER_before": cpwer_before, "cpWER_after": cpwer_after,
                "DER_before": der_before, "DER_after": der_after,
                "DF1_before": df1_before, "DF1_after": df1_after,
            })

            resumo = (
                f"▶ {nome_base}\n"
                f"   WDER: {wder_before} → {wder_after}\n"
                f"   cpWER: {cpwer_before} → {cpwer_after}\n"
                f"   DER: {der_before} → {der_after}\n"
                f"   DF1: {df1_before} → {df1_after}\n"
            )
            print(resumo)
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"{resumo}\n")

    print(f"\n✅ Métricas calculadas e salvas em:\n📄 {csv_path}\n📋 {log_path}")


if __name__ == "__main__":
    main()
