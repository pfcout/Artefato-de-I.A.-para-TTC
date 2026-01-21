"""
Script: validacao_garcia_spin.py
Autor: Projeto SPIN Zero-Shot
Descrição: Avaliação estatística conforme Garcia et al. (2025)
Métricas: AUC, F1, Run Consistency (RCR) e Spearman ρ
"""

import os
import pandas as pd
from sklearn.metrics import roc_auc_score, f1_score
from scipy.stats import spearmanr
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RUN1_PATH = BASE_DIR / ".." / "saida_excel" / "resultados_completos_SPIN.xlsx"
RUN2_PATH = BASE_DIR / ".." / "saida_excel" / "resultados_completos_SPIN_RUN2.xlsx"
HUMANO_PATH = BASE_DIR / ".." / "avaliacao_humana_SPIN.xlsx"

OUT_DIR_TXT = BASE_DIR / ".." / "saida_avaliacao" / "txt"
OUT_DIR_XLSX = BASE_DIR / ".." / "saida_avaliacao" / "excel"
OUT_DIR_TXT.mkdir(parents=True, exist_ok=True)
OUT_DIR_XLSX.mkdir(parents=True, exist_ok=True)

OUT_TXT = OUT_DIR_TXT / "validacao_garcia_spin.txt"
OUT_XLSX = OUT_DIR_XLSX / "validacao_garcia_spin.xlsx"

FASES = ["abertura", "situation", "problem", "implication", "need_payoff"]

print("🔍 Carregando planilhas...")
df1 = pd.read_excel(RUN1_PATH)
df2 = pd.read_excel(RUN2_PATH)
dfh = pd.read_excel(HUMANO_PATH) if HUMANO_PATH.exists() else None

for df in [df1, df2, dfh] if dfh is not None else [df1, df2]:
    if df is not None and "arquivo" in df.columns:
        df["arquivo"] = df["arquivo"].astype(str)

df = pd.merge(df1, df2, on="arquivo", suffixes=("_run1", "_run2"))
if dfh is not None:
    df = pd.merge(df, dfh, on="arquivo", how="left")

resultados = []
for fase in FASES:
    col1, col2 = f"{fase}_run1", f"{fase}_run2"
    if col1 not in df.columns or col2 not in df.columns:
        continue
    rcr = (df[col1] == df[col2]).mean()
    rho = spearmanr(df[col1], df[col2]).correlation

    auc, f1 = None, None
    colh = f"{fase}_h"
    if dfh is not None and colh in df.columns:
        try:
            auc = roc_auc_score(df[colh], df[col1])
        except Exception:
            auc = None
        try:
            f1 = f1_score(df[colh], df[col1])
        except Exception:
            f1 = None

    resultados.append({
        "fase": fase,
        "AUC": auc,
        "F1": f1,
        "RCR": rcr,
        "Spearman_rho": rho
    })

pd.DataFrame(resultados).to_excel(OUT_XLSX, index=False)
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("==== VALIDAÇÃO ESTATÍSTICA SPIN ZERO-SHOT ====
")
    f.write("Baseada em Garcia et al. (2025)

")
    for r in resultados:
        f.write(f"Fase: {r['fase']}
")
        f.write(f"  AUC: {r['AUC']:.3f}  F1: {r['F1']:.3f}  RCR: {r['RCR']:.3f}  ρ: {r['Spearman_rho']:.3f}

")
print("✅ Arquivos de validação criados com sucesso.")
