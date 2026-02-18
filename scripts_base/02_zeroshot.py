#!/usr/bin/env python3
# 02_zeroshot.py — v7.11+cli (Tele_IA / SPIN Analyzer)
#
# Objetivo:
#   - Ler .txt do 01 (ou benchmark via SPIN_IN_DIR / --input_dir)
#   - Rodar SPIN via Ollama usando Command Core
#   - Gerar Excel:
#       SPIN SELLING | CHECK_01 | CHECK_02 | RESULTADO TEXTO
#
# Regras:
#   - Sem regrinhas para decidir SPIN: LLM decide.
#   - Nosso código só analisa o que o LLM respondeu.
#   - RESULTADO TEXTO:
#       IDÊNTICO se CHECK_01 == CHECK_02, senão DIFERENTE.
#
# Toggle:
#   - SPIN_VENDOR_ONLY=1 (default) -> só vendedor
#   - SPIN_VENDOR_ONLY=0 -> inclui vendedor+cliente
#
# Env Vars importantes:
#   - SPIN_IN_DIR=/caminho/para/txts
#   - SPIN_OUT_DIR=/caminho/saida/excels
#   - SPIN_COMMAND_CORE_FILE=/caminho/absoluto/ou/relativo/ao/assets
#   - SPIN_FALLBACK_CORE_FILE=/caminho do prompt fallback (quando vier tudo 0/0)
#
# ===========================================================

import os
import re
import sys
import json
import time
import hashlib
import socket
import argparse
from datetime import datetime
from urllib import request
from urllib.error import URLError, HTTPError

from openpyxl import Workbook, load_workbook
import pandas as pd

# --------------------------
# PATH FIX
# --------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# --------------------------
# DEFAULTS (podem ser sobrescritos no main via CLI)
# --------------------------
DEFAULT_IN_DIR = os.path.join(ROOT_DIR, "arquivos_transcritos", "txt")
DEFAULT_OUT_DIR = os.path.join(ROOT_DIR, "saida_spin_excel")

IN_DIR = os.getenv("SPIN_IN_DIR", DEFAULT_IN_DIR)
OUT_DIR = (os.getenv("SPIN_OUT_DIR", "") or "").strip() or DEFAULT_OUT_DIR

SPIN_ONLY_FILE = (os.getenv("SPIN_ONLY_FILE", "") or "").strip()
WRITE_BATCH_FILE = (os.getenv("SPIN_WRITE_BATCH_FILE", "1") or "").strip() != "0"

SPIN_MAX_LINES_TOTAL = int(os.getenv("SPIN_MAX_LINES_TOTAL", "2000"))
SPIN_MAX_CHARS_TOTAL = int(os.getenv("SPIN_MAX_CHARS_TOTAL", "60000"))

SPIN_VENDOR_ONLY = (os.getenv("SPIN_VENDOR_ONLY", "1") or "1").strip() != "0"

# --------------------------
# OLLAMA
# --------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
OLLAMA_TIMEOUT_S = int(os.getenv("OLLAMA_TIMEOUT_S", "900"))
OLLAMA_TIMEOUT_RETRIES = int(os.getenv("OLLAMA_TIMEOUT_RETRIES", "1"))

OLLAMA_OPTIONS = {
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0")),
    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "2048")),
    "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "120")),
    "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
    "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.06")),
    "stop": ["```", "</s>"],
}

PHASES = ["P0_abertura", "P1_situation", "P2_problem", "P3_implication", "P4_need_payoff"]

# --------------------------
# COMMAND CORE
# --------------------------
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")
COMMAND_CORE_FILE = (os.getenv("SPIN_COMMAND_CORE_FILE", "") or "").strip()

def _resolve_command_core_path(cmd: str) -> str:
    """
    Aceita:
      - caminho absoluto: /root/.../Prompt_01.txt
      - caminho relativo ao assets: prompts_spin/Prompt_01.txt
      - nome de arquivo dentro de assets: Command_Core_D_Check_V2_6.txt
    """
    if not cmd:
        return ""

    # absoluto
    if os.path.isabs(cmd) and os.path.exists(cmd):
        return cmd

    # relativo: tenta dentro de assets/
    p1 = os.path.join(ASSETS_DIR, cmd)
    if os.path.exists(p1):
        return p1

    # se veio só nome, tenta direto em assets
    p2 = os.path.join(ASSETS_DIR, os.path.basename(cmd))
    if os.path.exists(p2):
        return p2

    return ""

def load_command_core() -> str:
    # 1) se setar SPIN_COMMAND_CORE_FILE, respeita
    if COMMAND_CORE_FILE:
        p = _resolve_command_core_path(COMMAND_CORE_FILE)
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                txt = (f.read() or "").strip()
                if txt:
                    return txt
        raise RuntimeError(f"SPIN_COMMAND_CORE_FILE setado mas não encontrado: {COMMAND_CORE_FILE}")

    # 2) fallback
    for p in [
        os.path.join(ASSETS_DIR, "Command_Core_D_Check_V3.txt"),
        os.path.join(ASSETS_DIR, "Command_Core_D_Check_V2.txt"),
        os.path.join(ASSETS_DIR, "Command_Core_D_Check.txt"),
        os.path.join(ASSETS_DIR, "command_core.txt"),
    ]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                txt = (f.read() or "").strip()
                if txt:
                    return txt

    return ""

COMMAND_CORE_RAW = load_command_core()
if not COMMAND_CORE_RAW:
    raise RuntimeError("Command Core não encontrado em assets/. Coloque V3 (recomendado) ou set SPIN_COMMAND_CORE_FILE.")

# --------------------------
# FALLBACK CORE (para casos all-zero / template-copy)
# --------------------------
FALLBACK_CORE_FILE = (os.getenv("SPIN_FALLBACK_CORE_FILE", "") or "").strip()
if not FALLBACK_CORE_FILE:
    # default: você já criou esse arquivo
    FALLBACK_CORE_FILE = os.path.join(ASSETS_DIR, "Command_Core_D_Check_V2_6_FALLBACK.txt")

def load_fallback_core() -> str:
    p = _resolve_command_core_path(FALLBACK_CORE_FILE)
    if p and os.path.exists(p):
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return (f.read() or "").strip()
    return ""

FALLBACK_CORE_RAW = load_fallback_core()

# --------------------------
# CACHE (inicializa depois de OUT_DIR ser definitivo)
# --------------------------
CACHE_DIR = None  # setado no main

def sha256_text(s: str) -> str:
    s = "" if s is None else str(s)
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

def cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f"{key}.json")

def cache_get(key: str):
    p = cache_path(key)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def cache_set(key: str, obj: dict):
    try:
        with open(cache_path(key), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# --------------------------
# TEXTO
# --------------------------
TAG_RE = re.compile(r"^\s*(\[(VENDEDOR|CLIENTE)\]|(VENDEDOR|CLIENTE|AGENTE|ATENDENTE)\s*:)\s*", re.IGNORECASE)

def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return str(f.read() or "")

def limit_text(txt: str) -> str:
    txt = "" if txt is None else str(txt)
    lines = txt.splitlines()
    if SPIN_MAX_LINES_TOTAL > 0:
        lines = lines[:SPIN_MAX_LINES_TOTAL]
    out = "\n".join(lines).strip()
    if SPIN_MAX_CHARS_TOTAL > 0 and len(out) > SPIN_MAX_CHARS_TOTAL:
        out = out[:SPIN_MAX_CHARS_TOTAL].rstrip()
    return out

def extract_vendor_only(txt: str) -> str:
    txt = limit_text(txt)
    lines = txt.splitlines()

    vendor_lines = []
    saw_vendor = False

    for line in lines:
        s = (line or "").strip()
        if not s:
            continue
        m = TAG_RE.match(s)
        if not m:
            continue

        head = (m.group(0) or "").strip().lower()
        content = TAG_RE.sub("", s).strip()
        if not content:
            continue

        if ("vendedor" in head) or ("agente" in head) or ("atendente" in head) or head.startswith("[vendedor]"):
            saw_vendor = True
            vendor_lines.append(f"[VENDEDOR] {content}")

    if saw_vendor and vendor_lines:
        return "\n".join(vendor_lines).strip()

    return txt.strip()

# --------------------------
# PROMPT (core + anexo)
# --------------------------
def pack_command_core(core: str, filename: str) -> str:
    core = "" if core is None else str(core)
    today = datetime.now().strftime("%Y-%m-%d")
    core = core.replace("{NOME_DO_ARQUIVO_ANEXADO}", filename)
    core = core.replace("{DATA_ANALISE}", today)

    max_chars = int(os.getenv("SPIN_CORE_MAX_CHARS", "18000"))
    if len(core) > max_chars:
        core = core[:max_chars].rstrip()
    return core

def build_prompt(core_packed: str, text_for_llm: str) -> str:
    text_for_llm = limit_text(text_for_llm)
    return f"""{core_packed}

[ANEXO — TRANSCRIÇÃO]
{text_for_llm}

[LEMBRETE FINAL — OBRIGATÓRIO]
Responda SOMENTE com as 6 linhas TSV no formato pedido (1 header + 5 linhas).
Não escreva explicações, títulos, listas ou texto extra.
"""

# --------------------------
# OLLAMA CALL
# --------------------------
def ollama_generate(prompt: str, timeout_s: int) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": OLLAMA_OPTIONS,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(OLLAMA_TIMEOUT_RETRIES + 1):
        try:
            with request.urlopen(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                obj = json.loads(raw)
                return (obj.get("response") or "").strip()
        except (socket.timeout, TimeoutError) as e:
            if attempt < OLLAMA_TIMEOUT_RETRIES:
                time.sleep(2 + attempt * 2)
                continue
            raise RuntimeError(f"timed out (timeout={timeout_s}s)") from e
        except (HTTPError, URLError) as e:
            raise RuntimeError(f"ollama api error: {e}") from e
        except Exception as e:
            raise RuntimeError(str(e)) from e

# --------------------------
# PARSE ROBUSTO (sem decidir SPIN)
# --------------------------
def _to01(x) -> str:
    x = "" if x is None else str(x)
    x = x.strip()
    if x in ("1", "1.0", "true", "True"):
        return "1"
    return "0"

def normalize_markdown_table_to_lines(out: str) -> list[str]:
    lines = []
    for raw in (out or "").splitlines():
        s = (raw or "").strip()
        if not s:
            continue

        # markdown table
        if s.startswith("|") and s.endswith("|"):
            if re.match(r"^\|\s*-+\s*\|", s):
                continue
            parts = [p.strip() for p in s.strip("|").split("|")]
            if not parts:
                continue
            if parts[0].lower() == "spin selling":
                continue
            if parts[0] in PHASES:
                nums = []
                for p in parts[1:]:
                    p = (p or "").strip()
                    if p in ("0", "1", "0.0", "1.0", "true", "false", "True", "False"):
                        nums.append(_to01(p))
                if len(nums) >= 2:
                    # mantém tolerância: se vier 2 ou 3 cols, guarda as 2 primeiras
                    lines.append(parts[0] + "\t" + "\t".join(nums[:3]))
            continue

        lines.append(s)
    return lines

def parse_table(output: str) -> dict:
    output = "" if output is None else str(output)
    rows = {ph: {"check1": "0", "check2": "0"} for ph in PHASES}

    lines = normalize_markdown_table_to_lines(output)

    for line in lines:
        s = (line or "").strip()
        for ph in PHASES:
            if s.startswith(ph):
                parts = s.split("\t")
                if len(parts) < 3:
                    parts = re.split(r"\s{2,}", s)
                if len(parts) < 3:
                    parts = re.split(r"\s+", s)

                vals = []
                for p in parts[1:]:
                    p = (p or "").strip()
                    if p in ("0", "1", "0.0", "1.0", "true", "false", "True", "False"):
                        vals.append(_to01(p))
                    if len(vals) == 2:
                        break

                if len(vals) == 2:
                    rows[ph]["check1"], rows[ph]["check2"] = vals
                break

    return rows

def is_valid_tsv(out: str) -> bool:
    if not out:
        return False
    lines = [l for l in (out or "").splitlines() if l.strip()]
    if len(lines) != 6:
        return False
    if not lines[0].startswith("SPIN SELLING"):
        return False
    phases = ["P0_abertura", "P1_situation", "P2_problem", "P3_implication", "P4_need_payoff"]
    for ph, line in zip(phases, lines[1:]):
        if not line.startswith(ph + "\t"):
            return False
    return True

def is_all_zero(table_rows: dict) -> bool:
    for ph in PHASES:
        c1 = _to01(table_rows.get(ph, {}).get("check1", "0"))
        c2 = _to01(table_rows.get(ph, {}).get("check2", "0"))
        if c1 == "1" or c2 == "1":
            return False
    return True

def read_table_rows_from_excel(xlsx_path: str) -> dict:
    rows = {ph: {"check1": "0", "check2": "0"} for ph in PHASES}
    wb = load_workbook(xlsx_path)
    ws = wb.active
    for r in range(1, ws.max_row + 1):
        a = ws.cell(r, 1).value
        if a in PHASES:
            b = ws.cell(r, 2).value
            c = ws.cell(r, 3).value
            rows[a]["check1"] = _to01(b)
            rows[a]["check2"] = _to01(c)
    return rows

def dump_debug(out_dir: str, in_path: str, kind: str, content: str):
    try:
        _dbg_dir = os.path.join(out_dir, "_debug_ollama")
        os.makedirs(_dbg_dir, exist_ok=True)
        _base = os.path.splitext(os.path.basename(in_path))[0]
        with open(os.path.join(_dbg_dir, f"{_base}.{kind}.txt"), "w", encoding="utf-8") as fp:
            fp.write(content or "")
    except Exception as _e:
        print("[warn] dump debug falhou:", _e)

def resultado_texto(c1: str, c2: str) -> str:
    return "IDÊNTICO" if _to01(c1) == _to01(c2) else "DIFERENTE"

def format_spin_summary(table_rows: dict) -> str:
    parts = []
    for ph in PHASES:
        c1 = table_rows.get(ph, {}).get("check1", "0")
        c2 = table_rows.get(ph, {}).get("check2", "0")
        parts.append(f"{ph}=({_to01(c1)}/{_to01(c2)})")
    return " ".join(parts)

# --------------------------
# EXCEL (sem RESULTADO numérico)
# --------------------------
def write_excel_like_model(out_xlsx: str, transcript_title: str, table_rows: dict):
    wb = Workbook()
    ws = wb.active
    ws.title = "Planilha1"

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 18

    ws["A1"] = str(transcript_title)
    ws["A3"] = "SPIN SELLING"
    ws["B3"] = "CHECK_01"
    ws["C3"] = "CHECK_02"
    ws["D3"] = "RESULTADO TEXTO"

    r = 4
    for ph in PHASES:
        c1 = table_rows.get(ph, {}).get("check1", "0")
        c2 = table_rows.get(ph, {}).get("check2", "0")
        ws[f"A{r}"] = ph
        ws[f"B{r}"] = int(_to01(c1))
        ws[f"C{r}"] = int(_to01(c2))
        ws[f"D{r}"] = resultado_texto(c1, c2)
        r += 1

    wb.save(out_xlsx)

def write_batch_excel(out_xlsx: str, blocks: list):
    wb = Workbook()
    ws = wb.active
    ws.title = "Planilha1"

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 18

    row = 1
    for (title, table_rows) in blocks:
        ws[f"A{row}"] = str(title)
        row += 1

        ws[f"A{row}"] = "SPIN SELLING"
        ws[f"B{row}"] = "CHECK_01"
        ws[f"C{row}"] = "CHECK_02"
        ws[f"D{row}"] = "RESULTADO TEXTO"
        row += 1

        for ph in PHASES:
            c1 = table_rows.get(ph, {}).get("check1", "0")
            c2 = table_rows.get(ph, {}).get("check2", "0")
            ws[f"A{row}"] = ph
            ws[f"B{row}"] = int(_to01(c1))
            ws[f"C{row}"] = int(_to01(c2))
            ws[f"D{row}"] = resultado_texto(c1, c2)
            row += 1

        row += 1

    wb.save(out_xlsx)

# --------------------------
# HELPERS DE TEMPO
# --------------------------
def fmt_hms(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"

# --------------------------
# CLI
# --------------------------
def parse_args():
    p = argparse.ArgumentParser(
        description="SPIN Analyzer 02_zeroshot (Tele_IA) — presence detection (double-check) -> Excel"
    )
    p.add_argument("--input_dir", default="", help="Pasta com .txt para análise (prioridade máxima).")
    p.add_argument("--run", default="", help="Nome do run. Se setado, salva em OUT_DIR/_runs/run_<run>/")
    p.add_argument("--only_file", default="", help="Processar apenas um arquivo específico (ex: teste_01.txt).")
    p.add_argument("--no_batch", action="store_true", help="Não gerar o Excel do lote.")
    return p.parse_args()

def resolve_in_dir(cli_input_dir: str) -> str:
    # 1) CLI manda (e NÃO pode ter fallback silencioso)
    if cli_input_dir and cli_input_dir.strip():
        p = os.path.abspath(os.path.expanduser(cli_input_dir.strip()))
        if not os.path.isdir(p):
            raise SystemExit(f"[fatal] --input_dir não existe ou não é pasta: {p}")
        return p

    # 2) ENV
    env_dir = (os.getenv("SPIN_IN_DIR", "") or "").strip()
    if env_dir:
        p = os.path.abspath(os.path.expanduser(env_dir))
        if not os.path.isdir(p):
            raise SystemExit(f"[fatal] SPIN_IN_DIR setado mas pasta não existe: {p}")
        return p

    # 3) default
    if not os.path.isdir(DEFAULT_IN_DIR):
        raise SystemExit(f"[fatal] Pasta default de entrada não existe: {DEFAULT_IN_DIR}")
    return DEFAULT_IN_DIR

def resolve_out_dir(cli_run: str) -> str:
    base = (os.getenv("SPIN_OUT_DIR", "") or "").strip() or DEFAULT_OUT_DIR
    base = os.path.abspath(os.path.expanduser(base))
    os.makedirs(base, exist_ok=True)

    run = (cli_run or "").strip()
    if not run:
        return base

    # padrão de execução isolada
    out = os.path.join(base, "_runs", f"run_{run}")
    os.makedirs(out, exist_ok=True)
    return out

# --------------------------
# MAIN
# --------------------------
def main():
    global IN_DIR, OUT_DIR, CACHE_DIR, SPIN_ONLY_FILE, WRITE_BATCH_FILE

    args = parse_args()

    # resolve paths com prioridade correta
    IN_DIR = resolve_in_dir(args.input_dir)
    OUT_DIR = resolve_out_dir(args.run)

    # opcional via CLI: apenas um arquivo
    if args.only_file and args.only_file.strip():
        SPIN_ONLY_FILE = args.only_file.strip()

    # opcional via CLI: sem batch
    if args.no_batch:
        WRITE_BATCH_FILE = False

    # cache dentro do OUT_DIR final (run-safe)
    CACHE_DIR = os.path.join(OUT_DIR, ".cache_spin02")
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    t_global_0 = time.time()
    start_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("===========================================================")
    print("🧠 02_zeroshot — SPIN Analyzer (v7.11+cli)")
    print(f"⏱️  Início: {start_ts}")
    print(f"📥 IN_DIR : {IN_DIR}")
    print(f"📤 OUT_DIR: {OUT_DIR}")
    if (args.run or "").strip():
        print(f"🏷️  RUN    : {args.run.strip()}")
    print(f"🤖 OLLAMA : {OLLAMA_MODEL} | timeout={OLLAMA_TIMEOUT_S}s | retries={OLLAMA_TIMEOUT_RETRIES}")
    print(f"🧾 Vendor-only: {'SIM' if SPIN_VENDOR_ONLY else 'NÃO'}")
    if COMMAND_CORE_FILE:
        print(f"🧩 Command Core (env): {COMMAND_CORE_FILE}")
    else:
        print("🧩 Command Core: fallback (assets)")
    if FALLBACK_CORE_RAW:
        print(f"🛟 Fallback Core: {FALLBACK_CORE_FILE}")
    else:
        print("🛟 Fallback Core: (não encontrado / desativado)")
    if SPIN_ONLY_FILE:
        print(f"🎯 ONLY_FILE: {SPIN_ONLY_FILE}")
    print("===========================================================")

    files = sorted([f for f in os.listdir(IN_DIR) if f.lower().endswith(".txt")])

    if SPIN_ONLY_FILE:
        files = [f for f in files if f == SPIN_ONLY_FILE]
        if not files:
            print(f"⛔ SPIN_ONLY_FILE='{SPIN_ONLY_FILE}' não encontrado em {IN_DIR}")
            return

    print(f"📂 Arquivos TXT para análise ({len(files)}):", files[:10], ("..." if len(files) > 10 else ""))
    if not files:
        print("⚠️ Nenhum .txt encontrado.")
        return

    blocks_for_batch = []
    batch_tag = datetime.now().strftime("%Y%m%d_%H%M%S")

    n = len(files)
    per_file_times = []

    for idx, f in enumerate(files, start=1):
        in_path = os.path.join(IN_DIR, f)
        stem = os.path.splitext(f)[0]
        title = stem
        out_xlsx = os.path.join(OUT_DIR, f"{stem}_SPIN.xlsx")

        # ================================
        # REUSE INDIVIDUAL (REAL)
        # ================================
        if os.path.exists(out_xlsx):
            try:
                table_rows = read_table_rows_from_excel(out_xlsx)
                print(f"\n↪️  Pulando Ollama (já existe): {out_xlsx}")
                print(f"🧾 SPIN (reused) = {format_spin_summary(table_rows)}")
                blocks_for_batch.append((title, table_rows))
                continue
            except Exception as e:
                print(f"\n[warn] Falha lendo Excel existente, vai recalcular: {e}")

        raw_txt = read_txt(in_path)

        if SPIN_VENDOR_ONLY:
            text_for_llm = extract_vendor_only(raw_txt)
        else:
            text_for_llm = limit_text(raw_txt)

        core_packed = pack_command_core(COMMAND_CORE_RAW, f)

        # cache key inclui hash do core principal (evita cache sujo quando core muda)
        key = sha256_text("|".join([
            "spin02_v7_11_cli",
            OLLAMA_MODEL,
            sha256_text(COMMAND_CORE_RAW),
            sha256_text(core_packed),
            sha256_text(text_for_llm),
            str(int(SPIN_VENDOR_ONLY)),
            f
        ]))

        cached = cache_get(key)
        if cached and isinstance(cached, dict) and cached.get("table_rows"):
            table_rows = cached["table_rows"]
            print(f"\n⚡ Cache hit [{idx}/{n}]: {f}")
            print(f"🧾 SPIN = {format_spin_summary(table_rows)}")
        else:
            prompt = build_prompt(core_packed, text_for_llm)

            print(f"\n📄 [{idx}/{n}] TXT: {f}")
            print("🧠 Analisando (Ollama)...")
            t0 = time.time()
            out = ""
            err = ""

            try:
                out = ollama_generate(prompt, timeout_s=OLLAMA_TIMEOUT_S)

                # dump debug principal (prompt + raw output)
                dump_debug(OUT_DIR, in_path, "prompt", prompt)
                dump_debug(OUT_DIR, in_path, "response", out or "")

            except Exception as e:
                err = str(e)
                print(f"   ⛔ Erro: {err}")
                out = ""

            dt = time.time() - t0
            per_file_times.append(dt)

            # ETA simples
            if len(per_file_times) >= 3:
                avg = sum(per_file_times[-10:]) / max(1, len(per_file_times[-10:]))
                remaining = (n - idx) * avg
                print(f"   ✅ Resposta em {dt:.1f}s | média~{avg:.1f}s | ETA~{fmt_hms(remaining)}")
            else:
                print(f"   ✅ Resposta em {dt:.1f}s")

            # parse
            table_rows = parse_table(out)

            # ----------------------------
            # FALLBACK: se veio tudo 0/0
            # ----------------------------
            used_fallback = False
            if is_all_zero(table_rows) and FALLBACK_CORE_RAW:
                print("   ⚠️ All-zero detectado. Rodando fallback (1x)...")
                try:
                    core_fb = pack_command_core(FALLBACK_CORE_RAW, f)
                    prompt_fb = build_prompt(core_fb, text_for_llm)
                    out_fb = ollama_generate(prompt_fb, timeout_s=OLLAMA_TIMEOUT_S)

                    dump_debug(OUT_DIR, in_path, "fallback.prompt", prompt_fb)
                    dump_debug(OUT_DIR, in_path, "fallback.response", out_fb or "")

                    table_fb = parse_table(out_fb)
                    if not is_all_zero(table_fb):
                        table_rows = table_fb
                        used_fallback = True
                        print("   ✅ Fallback resolveu (não all-zero).")
                    else:
                        print("   ⚠️ Fallback também veio all-zero. Mantendo original.")
                except Exception as _e:
                    print("   ⚠️ Fallback falhou:", _e)

            print(f"🧾 SPIN = {format_spin_summary(table_rows)}")

            # salva cache (se fallback foi usado, ainda é ok cachear o RESULTADO final)
            cache_set(key, {
                "file": f,
                "model": OLLAMA_MODEL,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "error": err,
                "used_fallback": bool(used_fallback),
                "table_rows": table_rows,
                "raw_output": (out or "")[:12000],
            })

        write_excel_like_model(out_xlsx, title, table_rows)
        print(f"📄 Excel individual salvo: {out_xlsx}")

        blocks_for_batch.append((title, table_rows))

    if WRITE_BATCH_FILE and len(blocks_for_batch) >= 1:
        out_batch = os.path.join(OUT_DIR, f"SPIN_RESULTADOS_LOTE_{batch_tag}.xlsx")
        write_batch_excel(out_batch, blocks_for_batch)
        print(f"\n📦 Excel do lote salvo: {out_batch}")

    end_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_s = time.time() - t_global_0

    print("\n===========================================================")
    print("✅ 02_zeroshot FINALIZADO (v7.11+cli).")
    print(f"⏱️  Fim: {end_ts}")
    print(f"⌛ Duração total: {fmt_hms(total_s)}")
    print("===========================================================")

if __name__ == "__main__":
    main()
