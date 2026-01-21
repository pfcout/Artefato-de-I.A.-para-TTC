# ===========================================================
# 05_metricas_validacao.py
# Projeto: Tele_IA Transcrição
# Objetivo: comparar RUN1 vs RUN2 do 02_zeroshot.py
# Métricas: consistência por fase, RCR, score total, divergências
# Saídas: XLSX + TXT (resumo acadêmico)
# ===========================================================

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

RUN1_PATH = ROOT_DIR / "saida_excel" / "resultados_completos_SPIN_RUN1.xlsx"
RUN2_PATH = ROOT_DIR / "saida_excel" / "resultados_completos_SPIN_RUN2.xlsx"

OUT_DIR = ROOT_DIR / "saida_metricas"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_XLSX = OUT_DIR / "metricas_validacao.xlsx"
OUT_DIFF_XLSX = OUT_DIR / "diferencas_por_arquivo.xlsx"
OUT_TXT = OUT_DIR / "resumo_metricas.txt"

FASES = ["abertura", "situation", "problem", "implication", "need_payoff"]

# -----------------------------
# Helpers
# -----------------------------
def safe_int(x, default=0):
    try:
        return int(float(x))
    except Exception:
        return default

def carregar(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_excel(path)
    if df is None or df.empty:
        raise ValueError(f"Arquivo vazio: {path}")

    # Normalização mínima
    if "arquivo" not in df.columns:
        raise ValueError(f"Coluna 'arquivo' não encontrada em: {path}")

    df = df.copy()
    df["arquivo"] = df["arquivo"].astype(str).str.strip()

    # Garante colunas das fases
    for f in FASES:
        if f not in df.columns:
            df[f] = 0
        df[f] = df[f].apply(safe_int)

    # Score SPIN 20 (sem abertura)
    df["score20"] = df["situation"] + df["problem"] + df["implication"] + df["need_payoff"]
    # Score 25 (com abertura)
    df["score25"] = df["abertura"] + df["score20"]

    return df

def rcr_por_fase(df_join: pd.DataFrame, fase: str) -> float:
    """
    RCR simples: proporção de arquivos em que RUN1 == RUN2 naquela fase (0 ou 1)
    """
    col1 = f"{fase}_r1"
    col2 = f"{fase}_r2"
    iguais = (df_join[col1] == df_join[col2]).mean()
    return float(iguais)

def taxa_presenca(df: pd.DataFrame, fase: str) -> float:
    """
    Percentual de arquivos em que a fase apareceu (valor 1)
    """
    return float((df[fase] == 1).mean())

# -----------------------------
# Main
# -----------------------------
def main():
    print("== 05 Métricas de Validação (RUN1 vs RUN2) ==")

    df1 = carregar(RUN1_PATH)
    df2 = carregar(RUN2_PATH)

    # Junta por arquivo (inner = só os que existem em ambos)
    j = df1[["arquivo"] + FASES + ["score20", "score25"]].merge(
        df2[["arquivo"] + FASES + ["score20", "score25"]],
        on="arquivo",
        how="inner",
        suffixes=("_r1", "_r2"),
    )

    if j.empty:
        raise ValueError("Nenhum arquivo em comum entre RUN1 e RUN2. Verifique os Excels.")

    n = len(j)

    # Métricas por fase
    linhas = []
    for fase in FASES:
        rcr = rcr_por_fase(j, fase)

        pres1 = float((j[f"{fase}_r1"] == 1).mean())
        pres2 = float((j[f"{fase}_r2"] == 1).mean())

        diverg = int((j[f"{fase}_r1"] != j[f"{fase}_r2"]).sum())

        linhas.append({
            "fase": fase,
            "rcr_consistencia_(0-1)": round(rcr, 4),
            "presenca_run1_(0-1)": round(pres1, 4),
            "presenca_run2_(0-1)": round(pres2, 4),
            "divergencias_(qtd)": diverg,
            "total_arquivos": n,
        })

    df_metricas = pd.DataFrame(linhas)

    # Métricas globais
    # Consistência média simples (média dos RCRs)
    rcr_medio = float(df_metricas["rcr_consistencia_(0-1)"].mean())

    # Score25 idêntico?
    score25_igual = float((j["score25_r1"] == j["score25_r2"]).mean())
    score20_igual = float((j["score20_r1"] == j["score20_r2"]).mean())

    # Diferença média absoluta de score
    diff_abs_25 = float((j["score25_r1"] - j["score25_r2"]).abs().mean())
    diff_abs_20 = float((j["score20_r1"] - j["score20_r2"]).abs().mean())

    df_global = pd.DataFrame([{
        "amostras_em_comum": n,
        "rcr_medio_(0-1)": round(rcr_medio, 4),
        "score25_igual_(0-1)": round(score25_igual, 4),
        "score20_igual_(0-1)": round(score20_igual, 4),
        "diff_media_abs_score25": round(diff_abs_25, 4),
        "diff_media_abs_score20": round(diff_abs_20, 4),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }])

    # Arquivos que divergiram (para auditoria)
    divergencias = []
    for _, row in j.iterrows():
        diffs = []
        for fase in FASES:
            if row[f"{fase}_r1"] != row[f"{fase}_r2"]:
                diffs.append(fase)
        if diffs:
            divergencias.append({
                "arquivo": row["arquivo"],
                "fases_divergentes": ", ".join(diffs),
                "score25_run1": int(row["score25_r1"]),
                "score25_run2": int(row["score25_r2"]),
                "score20_run1": int(row["score20_r1"]),
                "score20_run2": int(row["score20_r2"]),
            })

    df_diff = pd.DataFrame(divergencias)

    # Salva Excel (2 abas + divergências)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df_global.to_excel(writer, index=False, sheet_name="global")
        df_metricas.to_excel(writer, index=False, sheet_name="por_fase")

    df_diff.to_excel(OUT_DIFF_XLSX, index=False)

    # Salva TXT acadêmico
    resumo = []
    resumo.append("TELE_IA — VALIDACAO (RUN1 vs RUN2)")
    resumo.append(f"Gerado em: {df_global.loc[0, 'gerado_em']}")
    resumo.append("")
    resumo.append(f"Amostras (arquivos em comum): {n}")
    resumo.append(f"RCR médio (consistência por fase): {rcr_medio:.3f}")
    resumo.append(f"Score 25 idêntico: {score25_igual:.3f}")
    resumo.append(f"Score 20 idêntico: {score20_igual:.3f}")
    resumo.append(f"Diferença média |Score25|: {diff_abs_25:.3f}")
    resumo.append(f"Diferença média |Score20|: {diff_abs_20:.3f}")
    resumo.append("")
    resumo.append("Consistência por fase (RCR):")
    for _, r in df_metricas.iterrows():
        resumo.append(f"- {r['fase']}: RCR={r['rcr_consistencia_(0-1)']}, divergências={r['divergencias_(qtd)']}/{n}")
    resumo.append("")
    resumo.append(f"Arquivos com divergência em alguma fase: {len(df_diff)}")
    resumo.append(f"Detalhes: {OUT_DIFF_XLSX.name}")

    OUT_TXT.write_text("\n".join(resumo), encoding="utf-8")

    print(f"[OK] Salvo: {OUT_XLSX}")
    print(f"[OK] Salvo: {OUT_DIFF_XLSX}")
    print(f"[OK] Salvo: {OUT_TXT}")

if __name__ == "__main__":
    main()
