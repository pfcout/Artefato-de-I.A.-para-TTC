#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

# ============================================================
# 🎯 CONFIG SPIN
# ============================================================

PHASES = [
    "P0_abertura",
    "P1_situation",
    "P2_problem",
    "P3_implication",
    "P4_need_payoff"
]
IDX = {p: i for i, p in enumerate(PHASES)}

TRUE_SET = {"✅", "✔", "1", "true", "True", "TRUE"}
FALSE_SET = {"❌", "✘", "✗", "0", "false", "False", "FALSE"}

# ============================================================
# 🔧 UTILS
# ============================================================

def norm(s: str) -> str:
    return re.sub(r"\s+", "_", (s or "").strip()).strip("_").lower()

def to01(x) -> int:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return 0
    s = str(x).strip()
    if s in TRUE_SET:
        return 1
    if s in FALSE_SET:
        return 0
    try:
        return int(float(s))
    except:
        return 0

def vec(d: Dict[str, int]) -> List[int]:
    return [int(d.get(p, 0)) for p in PHASES]

def extract_id_from_key(k: str) -> Optional[str]:
    m = re.search(r"(teste_\d+)", (k or "").lower())
    return m.group(1) if m else None

# ============================================================
# 📦 BLOCO
# ============================================================

@dataclass
class Block:
    key: str            # ex: "teste_01"
    norm_key: str       # ex: "teste_01"
    key_id: str         # ex: "teste_01"
    y: Dict[str, int]   # fases -> 0/1
    ok: bool
    row: int            # linha no excel onde começa o bloco

# ============================================================
# 📊 PARSE EXCEL (FORMATO "BLOCOS" DO 02)
# Excel do lote:
# linha: "teste_01"
# linha seguinte: "SPIN SELLING | CHECK_01 | CHECK_02 | RESULTADO TEXTO"
# próximas 5 linhas: fase na colA, check_01 colB, check_02 colC
# ============================================================

def parse_excel_blocks(path: str, pred_col: str = "CHECK_02") -> List[Block]:
    df = pd.read_excel(path, header=None, engine="openpyxl").fillna("")

    # encontra inícios dos blocos: colA = "teste_XX"
    starts = []
    for i in range(len(df)):
        v = str(df.iat[i, 0]).strip().lower()
        if re.fullmatch(r"teste_\d+", v):
            starts.append(i)

    blocks: List[Block] = []

    for i, s in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(df)

        key_raw = str(df.iat[s, 0]).strip()
        key_n = norm(key_raw)
        key_id = extract_id_from_key(key_n) or key_n

        # procura a linha "SPIN SELLING" logo após o teste_XX
        header_row = None
        for r in range(s, min(s + 6, end)):
            if str(df.iat[r, 0]).strip().upper() == "SPIN SELLING":
                header_row = r
                break

        y: Dict[str, int] = {}
        if header_row is not None:
            # linhas de fases esperadas: header_row+1..header_row+5
            for r in range(header_row + 1, min(header_row + 6, end)):
                phase = str(df.iat[r, 0]).strip()
                if phase in PHASES:
                    if pred_col == "CHECK_01":
                        val = df.iat[r, 1]
                    else:
                        val = df.iat[r, 2]
                    y[phase] = to01(val)

        ok = all(p in y for p in PHASES)

        blocks.append(Block(
            key=key_raw,
            norm_key=key_n,
            key_id=key_id,
            y=y,
            ok=ok,
            row=s
        ))

    return blocks

# ============================================================
# 📑 PARSE EXPECTED (NOVO GABARITO: 100 TSVs)
# /root/analyze_service/repo/benchmark_expected/avaliacao_teste_01.tsv
# Conteúdo: deve ter linhas com P0_abertura..P4_need_payoff e 0/1
# Aceita TSV de 2 colunas: fase \t valor
# Também aceita header (ignora)
# ============================================================

def parse_expected_dir(expected_dir: str) -> Dict[str, Dict[str, int]]:
    exp: Dict[str, Dict[str, int]] = {}
    if not os.path.isdir(expected_dir):
        raise ValueError(f"--expected precisa ser uma pasta. Recebi: {expected_dir}")

    files = sorted([
        f for f in os.listdir(expected_dir)
        if f.lower().endswith(".tsv")
    ])

    for fn in files:
        path = os.path.join(expected_dir, fn)

        # tenta extrair id do nome do arquivo
        m = re.search(r"(teste[_\-]?)(\d+)", fn.lower())
        if not m:
            continue
        num = int(m.group(2))
        key = norm(f"teste_{num:02d}")

        y = {p: 0 for p in PHASES}

        with open(path, "r", encoding="utf-8") as f:
            for line in f.read().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                phase = parts[0].strip()
                val = parts[1].strip()

                if phase in PHASES:
                    y[phase] = to01(val)

        exp[key] = y

    return exp

# ============================================================
# 📐 MÉTRICAS BASE
# ============================================================

def confusion(YT, YP, i):
    tp = tn = fp = fn = 0
    for t, p in zip(YT, YP):
        if t[i] == 1 and p[i] == 1:
            tp += 1
        elif t[i] == 0 and p[i] == 0:
            tn += 1
        elif t[i] == 0 and p[i] == 1:
            fp += 1
        elif t[i] == 1 and p[i] == 0:
            fn += 1
    return tp, tn, fp, fn

def acc(tp, tn, fp, fn):
    den = tp + tn + fp + fn
    return (tp + tn) / den if den else 0

def bal_acc(tp, tn, fp, fn):
    r1 = tp / (tp + fn) if tp + fn else 0
    r0 = tn / (tn + fp) if tn + fp else 0
    return (r1 + r0) / 2

def prec(tp, fp):
    return tp / (tp + fp) if tp + fp else 0

def rec(tp, fn):
    return tp / (tp + fn) if tp + fn else 0

def f1(p, r):
    return 0 if p + r == 0 else 2 * p * r / (p + r)

def micro_PRF(YT, YP, idxs):
    TP = FP = FN = 0
    for t, p in zip(YT, YP):
        for i in idxs:
            if t[i] == 1 and p[i] == 1:
                TP += 1
            elif t[i] == 0 and p[i] == 1:
                FP += 1
            elif t[i] == 1 and p[i] == 0:
                FN += 1
    P = TP / (TP + FP) if TP + FP else 0
    R = TP / (TP + FN) if TP + FN else 0
    return P, R, f1(P, R)

def macro_PRF(YT, YP, idxs):
    Ps = Rs = Fs = 0
    for i in idxs:
        tp, tn, fp, fn = confusion(YT, YP, i)
        p = prec(tp, fp)
        r = rec(tp, fn)
        Ps += p
        Rs += r
        Fs += f1(p, r)
    n = len(idxs)
    return Ps / n, Rs / n, Fs / n

def exact(YT, YP, idxs=None):
    ok = 0
    use = range(5) if idxs is None else idxs
    for t, p in zip(YT, YP):
        ok += int(all(t[i] == p[i] for i in use))
    return ok / len(YT) if YT else 0

def micro_acc(YT, YP, idxs):
    c = t = 0
    for trow, prow in zip(YT, YP):
        for i in idxs:
            t += 1
            c += int(trow[i] == prow[i])
    return c / t if t else 0

def jaccard_no_p0(YT, YP):
    vals = []
    for t, p in zip(YT, YP):
        a = {i for i in range(1, 5) if t[i] == 1}
        b = {i for i in range(1, 5) if p[i] == 1}
        vals.append(1 if not a and not b else len(a & b) / len(a | b))
    return sum(vals) / len(vals) if vals else 0

def hamming(YT, YP, idxs):
    err = tot = 0
    for t, p in zip(YT, YP):
        for i in idxs:
            tot += 1
            err += int(t[i] != p[i])
    return err / tot if tot else 0

def bootstrap(metric, pairs, n=2000, seed=42):
    rng = random.Random(seed)
    vals = []
    for _ in range(n):
        samp = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        yt = [x for x, _ in samp]
        yp = [y for _, y in samp]
        vals.append(metric(yt, yp))
    vals.sort()
    mid = metric([x for x, _ in pairs], [y for _, y in pairs])
    return mid, vals[int(.025 * n)], vals[int(.975 * n)]

# ============================================================
# 🧾 EXPORTS BONITOS
# ============================================================

def write_pretty_txt(outdir, summary_lines, per_phase_lines, explain_lines):
    p = os.path.join(outdir, "metrics_report_pretty.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n\n")
        f.write("📌 Por etapa (acc | bal_acc | P/R/F1 | TP/TN/FP/FN)\n")
        f.write("-" * 70 + "\n")
        f.write("\n".join(per_phase_lines) + "\n\n")
        f.write("🧠 Mini explicações\n")
        f.write("-" * 70 + "\n")
        f.write("\n".join(explain_lines) + "\n")
    print(f"[ok] wrote: {p}")

def write_excel(outdir, df_summary, df_phase, df_align, df_explain):
    p = os.path.join(outdir, "metrics_pretty.xlsx")
    with pd.ExcelWriter(p, engine="openpyxl") as w:
        df_summary.to_excel(w, sheet_name="📌_Resumo", index=False)
        df_phase.to_excel(w, sheet_name="🎯_Por_Fase", index=False)
        df_align.to_excel(w, sheet_name="🧪_Sanity_Check", index=False)
        df_explain.to_excel(w, sheet_name="🧠_Explicações", index=False)
    print(f"[ok] wrote: {p}")

# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", required=True)
    ap.add_argument("--expected", required=True, help="Pasta com 100 TSVs (avaliacao_teste_XX.tsv)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--pred_col", choices=["CHECK_01", "CHECK_02"], default="CHECK_02")
    ap.add_argument("--bootstrap_n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # 1) parse excel (blocos)
    blocks = parse_excel_blocks(args.excel, pred_col=args.pred_col)
    exp = parse_expected_dir(args.expected)

    # debug counts
    blocks_ok = [b for b in blocks if b.ok]
    print(f"[excel] blocks detected (total): {len(blocks)} | ok(5 fases): {len(blocks_ok)}")
    print(f"[expected] keys parsed: {len(exp)}")

    # 2) index preds por key_id (teste_01..)
    pred_by_id = {b.key_id: b for b in blocks_ok}

    # 3) align
    aligned = []
    unmatched_expected = []
    unmatched_pred = set(pred_by_id.keys())

    for kexp, yexp in exp.items():
        kid = extract_id_from_key(kexp) or kexp
        chosen = pred_by_id.get(kid)
        if not chosen:
            unmatched_expected.append(kexp)
            continue

        unmatched_pred.discard(kid)

        yt = vec(yexp)
        yp = vec(chosen.y)

        aligned.append({
            "key": kexp,
            "y_true_P0": yt[0], "y_true_P1": yt[1], "y_true_P2": yt[2], "y_true_P3": yt[3], "y_true_P4": yt[4],
            "y_pred_P0": yp[0], "y_pred_P1": yp[1], "y_pred_P2": yp[2], "y_pred_P3": yp[3], "y_pred_P4": yp[4],
            "ok_parse": int(chosen.ok),
            "source_row_start": int(chosen.row),
            "matched_pred_key": chosen.norm_key,
            "matched_pred_id": chosen.key_id
        })

    print(f"[alignment] expected without prediction: {len(unmatched_expected)}")
    if unmatched_expected:
        for k in unmatched_expected[:30]:
            print("  -", k)

    print(f"[alignment] predictions without expected: {len(unmatched_pred)}")
    if unmatched_pred:
        for k in sorted(list(unmatched_pred))[:30]:
            print("  -", k)

    df_align = pd.DataFrame(aligned)
    sanity = os.path.join(args.outdir, "sanity_check_alignment.csv")
    df_align.to_csv(sanity, index=False, encoding="utf-8")
    print(f"[ok] wrote: {sanity}")

    if df_align.empty:
        print("[fatal] no aligned rows.")
        return

    # 4) arrays
    YT = [[r["y_true_P0"], r["y_true_P1"], r["y_true_P2"], r["y_true_P3"], r["y_true_P4"]] for r in aligned]
    YP = [[r["y_pred_P0"], r["y_pred_P1"], r["y_pred_P2"], r["y_pred_P3"], r["y_pred_P4"]] for r in aligned]
    pairs = list(zip(YT, YP))

    idx_all = [0, 1, 2, 3, 4]
    idx_np0 = [1, 2, 3, 4]

    # 5) métricas globais
    acc_all = micro_acc(YT, YP, idx_all)
    acc_np0 = micro_acc(YT, YP, idx_np0)

    em_all = exact(YT, YP, idxs=None)
    em_np0 = exact(YT, YP, idxs=idx_np0)

    Pm_all, Rm_all, Fm_all = macro_PRF(YT, YP, idx_all)
    Pi_all, Ri_all, Fi_all = micro_PRF(YT, YP, idx_all)

    Pm_np0, Rm_np0, Fm_np0 = macro_PRF(YT, YP, idx_np0)
    Pi_np0, Ri_np0, Fi_np0 = micro_PRF(YT, YP, idx_np0)

    jac_np0 = jaccard_no_p0(YT, YP)
    ham_all = hamming(YT, YP, idx_all)
    ham_np0 = hamming(YT, YP, idx_np0)

    mf1_mid, mf1_lo, mf1_hi = bootstrap(lambda yt, yp: micro_PRF(yt, yp, idx_all)[2], pairs, n=args.bootstrap_n, seed=args.seed)
    em_mid, em_lo, em_hi = bootstrap(lambda yt, yp: exact(yt, yp), pairs, n=args.bootstrap_n, seed=args.seed)
    emnp0_mid, emnp0_lo, emnp0_hi = bootstrap(lambda yt, yp: exact(yt, yp, idxs=idx_np0), pairs, n=args.bootstrap_n, seed=args.seed)

    # 6) por fase
    per_phase_lines = []
    per_phase_rows = []
    for ph, i in IDX.items():
        tp, tn, fp, fn = confusion(YT, YP, i)
        a = acc(tp, tn, fp, fn)
        ba = bal_acc(tp, tn, fp, fn)
        p = prec(tp, fp)
        r = rec(tp, fn)
        ff = f1(p, r)
        per_phase_lines.append(
            f"{ph}: acc={a*100:.2f}% bal_acc={ba*100:.2f}% "
            f"P={p*100:.2f}% R={r*100:.2f}% F1={ff*100:.2f}% "
            f"(TP={tp} TN={tn} FP={fp} FN={fn})"
        )
        per_phase_rows.append({
            "fase": ph,
            "acc": a,
            "bal_acc": ba,
            "precision": p,
            "recall": r,
            "f1": ff,
            "TP": tp, "TN": tn, "FP": fp, "FN": fn
        })

    explain_lines = [
        "✅ Acurácia micro: acertos/total de labels. Pode inflar quando há muitos zeros.",
        "⚖️ Balanced accuracy: média do recall da classe 1 e da classe 0 (boa com desbalanceamento).",
        "🎯 Precision: entre tudo que o modelo marcou 1, quanto era 1 (controla FP).",
        "📣 Recall: entre tudo que era 1, quanto recuperou (controla FN).",
        "🏆 F1: equilíbrio entre precision e recall.",
        "🎯 Exact match: acerto perfeito do vetor de fases (métrica rígida).",
        "🧩 Jaccard sem P0: similaridade do conjunto de fases detectadas (mais suave).",
        "🧷 Hamming loss: fração de labels erradas (menor é melhor).",
        "📈 Bootstrap CI 95%: intervalo de confiança por reamostragem.",
    ]

    n = len(YT)
    total_all = n * 5
    total_np0 = n * 4

    summary_lines = [
        "============================== 📊 MÉTRICAS — SPIN (benchmark) ==============================",
        f"Amostras avaliadas (alinhadas): {n}",
        "",
        f"✅ Acurácia global (P0..P4) [micro]: {acc_all*100:.2f}% ({int(acc_all*total_all)}/{total_all})",
        f"✅ Acurácia global SEM abertura (P1..P4) [micro]: {acc_np0*100:.2f}% ({int(acc_np0*total_np0)}/{total_np0})",
        f"🎯 Exact match (5/5): {em_all*100:.2f}% ({int(em_all*n)}/{n})",
        f"🎯 Exact match SEM abertura (4/4): {em_np0*100:.2f}% ({int(em_np0*n)}/{n})",
        "",
        "------------------------------",
        "📌 Precision / Recall / F1 (macro e micro)",
        "------------------------------",
        f"MACRO (P0..P4): P={Pm_all*100:.2f}% R={Rm_all*100:.2f}% F1={Fm_all*100:.2f}%",
        f"MICRO (P0..P4): P={Pi_all*100:.2f}% R={Ri_all*100:.2f}% F1={Fi_all*100:.2f}%",
        f"MACRO (P1..P4): P={Pm_np0*100:.2f}% R={Rm_np0*100:.2f}% F1={Fm_np0*100:.2f}%",
        f"MICRO (P1..P4): P={Pi_np0*100:.2f}% R={Ri_np0*100:.2f}% F1={Fi_np0*100:.2f}%",
        "",
        "------------------------------",
        "📌 Bootstrap CI 95% (robusto)",
        "------------------------------",
        f"micro-F1 (P0..P4): {mf1_mid*100:.2f}%  CI95% [{mf1_lo*100:.2f}%, {mf1_hi*100:.2f}%]",
        f"exact match (5/5): {em_mid*100:.2f}%  CI95% [{em_lo*100:.2f}%, {em_hi*100:.2f}%]",
        f"exact match SEM P0 (4/4): {emnp0_mid*100:.2f}%  CI95% [{emnp0_lo*100:.2f}%, {emnp0_hi*100:.2f}%]",
        "",
        "------------------------------",
        "📌 Extras (sem P0)",
        "------------------------------",
        f"Jaccard sem P0: {jac_np0*100:.2f}%",
        f"Hamming loss (P0..P4): {ham_all*100:.2f}%",
        f"Hamming loss (P1..P4): {ham_np0*100:.2f}%",
    ]

    print("\n" + "\n".join(summary_lines))
    print("\n------------------------------")
    print("📌 Por etapa (acc | bal_acc | P/R/F1 | TP/TN/FP/FN)")
    print("------------------------------")
    for l in per_phase_lines:
        print(l)

    df_summary = pd.DataFrame([{
        "n_aligned": n,
        "pred_col": args.pred_col,
        "acc_micro_all": acc_all,
        "acc_micro_no_p0": acc_np0,
        "exact_match_all": em_all,
        "exact_match_no_p0": em_np0,
        "macro_P_all": Pm_all, "macro_R_all": Rm_all, "macro_F1_all": Fm_all,
        "micro_P_all": Pi_all, "micro_R_all": Ri_all, "micro_F1_all": Fi_all,
        "macro_P_no_p0": Pm_np0, "macro_R_no_p0": Rm_np0, "macro_F1_no_p0": Fm_np0,
        "micro_P_no_p0": Pi_np0, "micro_R_no_p0": Ri_np0, "micro_F1_no_p0": Fi_np0,
        "microF1_CI_lo": mf1_lo, "microF1_CI_hi": mf1_hi,
        "exact_CI_lo": em_lo, "exact_CI_hi": em_hi,
        "exact_no_p0_CI_lo": emnp0_lo, "exact_no_p0_CI_hi": emnp0_hi,
        "jaccard_no_p0": jac_np0,
        "hamming_all": ham_all,
        "hamming_no_p0": ham_np0,
    }])

    df_phase = pd.DataFrame(per_phase_rows)
    df_explain = pd.DataFrame([{"item": x} for x in explain_lines])

    write_pretty_txt(args.outdir, summary_lines, per_phase_lines, explain_lines)
    write_excel(args.outdir, df_summary, df_phase, df_align, df_explain)

    p_simple = os.path.join(args.outdir, "metrics_report.txt")
    with open(p_simple, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n\n")
        f.write("📌 Por etapa (acc | bal_acc | P/R/F1 | TP/TN/FP/FN)\n")
        f.write("-" * 70 + "\n")
        f.write("\n".join(per_phase_lines) + "\n")
    print(f"[ok] wrote: {p_simple}")

if __name__ == "__main__":
    main()

