# ===============================================
# 🎧 SPIN Analyzer — Painel (TXT + WAV)
# Modo: Streamlit Cloud chamando serviço remoto via HTTP
# UX: dark premium (cliente-first), sem termos técnicos, sem TXT
# Robustez: não armazena ZIP inteiro nem mapas gigantes em st.session_state
# - Individual: abre Excel principal + download Excel
# - Lote: abre Excel consolidado + download (lote + por item)
# - Limites no lote:
#   • Áudio: até 5 arquivos • até 10 minutos cada
#   • Texto: até 8 entradas (arquivos + blocos colados)
# ===============================================

import os
import re
import io
import time
import zipfile
import wave
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import streamlit as st
import pandas as pd
import requests


# ==============================
# ⚙️ set_page_config PRIMEIRO
# ==============================
st.set_page_config(
    page_title="SPIN Analyzer — Avaliação de Ligações",
    page_icon="🎧",
    layout="wide",
)

# ==============================
# 🔐 Config (Secrets/Env)
# ==============================
def _get_cfg(key: str, default: str = "") -> str:
    v = os.getenv(key)
    if v is not None:
        return str(v).strip()
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return str(default).strip()


MODE = _get_cfg("MODE", "VPS").upper()
BASE_URL = _get_cfg("VPS_BASE_URL", "").rstrip("/")
API_KEY = _get_cfg("VPS_API_KEY", "")

CONNECT_TIMEOUT_S = int(_get_cfg("CONNECT_TIMEOUT_S", "10"))
READ_TIMEOUT_S = int(_get_cfg("API_TIMEOUT_S", "7200"))
REQ_TIMEOUT = (CONNECT_TIMEOUT_S, READ_TIMEOUT_S)

EXCEL_WRAP_TEXT = _get_cfg("EXCEL_WRAP_TEXT", "1").strip() not in ("0", "false", "False", "")
EXCEL_DEFAULT_COL_W = int(_get_cfg("EXCEL_DEFAULT_COL_W", "22"))
EXCEL_TEXT_COL_W = int(_get_cfg("EXCEL_TEXT_COL_W", "55"))
EXCEL_MAX_COL_W = int(_get_cfg("EXCEL_MAX_COL_W", "80"))

if MODE != "VPS":
    st.error("Este painel está configurado apenas para execução online. Ajuste a configuração do projeto.")
    st.stop()
if not BASE_URL:
    st.error("Configuração ausente: endereço do serviço.")
    st.stop()
if not API_KEY:
    st.error("Configuração ausente: chave de acesso.")
    st.stop()


# ==============================
# 🎨 DARK UI (força fundo preto)
# ==============================
st.markdown(
    """
<style>
:root{
  --bg:#070A12;
  --panel:#0B1020;
  --card:#0E1426;
  --card2:#101A33;
  --text:#EAF0FF;
  --muted:#A9B4CC;
  --line:#1B2747;
  --brand:#5B8CFF;
  --brand2:#8AB1FF;
  --ok:#2EE59D;
  --warn:#FFB020;
  --shadow: 0 10px 30px rgba(0,0,0,0.35);
}

/* App + containers */
html, body, [data-testid="stAppViewContainer"], .stApp{
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
}
.block-container{
  padding-top: 1.25rem;
  padding-bottom: 2.5rem;
}

/* Sidebar */
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, #070A12 0%, #060810 100%) !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] *{
  color: var(--text) !important;
}

/* Typography */
h1,h2,h3{ color: var(--text) !important; letter-spacing:-0.3px; }
hr{ border-color: var(--line) !important; }

/* Cards */
.card{
  background: linear-gradient(180deg, var(--card) 0%, var(--panel) 100%) !important;
  border: 1px solid var(--line) !important;
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: var(--shadow);
}
.card-tight{
  background: rgba(14,20,38,0.90) !important;
  border: 1px solid var(--line) !important;
  border-radius: 16px;
  padding: 12px 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.25);
}
.kicker{
  font-size: 0.9rem;
  font-weight: 800;
  color: var(--muted) !important;
  margin: 0 0 6px 0;
}
.title{
  margin: 0;
  font-size: 1.18rem;
  font-weight: 900;
  color: var(--text) !important;
}
.smallmuted{
  color: var(--muted) !important;
  font-weight: 650;
}
.section-title{
  margin:0;
  font-size: 1.05rem;
  font-weight: 900;
}

/* Badges */
.badges{ display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; }
.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid var(--line) !important;
  background: rgba(10,14,26,0.70) !important;
  color: var(--muted) !important;
  font-weight: 850;
  font-size: 0.9rem;
}
.badge.ok{
  border-color: rgba(46,229,157,0.22) !important;
  background: rgba(46,229,157,0.10) !important;
  color: #B7FFE6 !important;
}
.badge.brand{
  border-color: rgba(91,140,255,0.25) !important;
  background: rgba(91,140,255,0.10) !important;
  color: var(--brand2) !important;
}
.badge.warn{
  border-color: rgba(255,176,32,0.25) !important;
  background: rgba(255,176,32,0.10) !important;
  color: #FFE2A6 !important;
}

/* Inputs */
textarea, input, .stTextArea textarea, .stTextInput input{
  background: rgba(8,11,20,0.65) !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
}
label{ color: var(--muted) !important; font-weight: 700 !important; }

/* Buttons */
button{
  border-radius: 14px !important;
}
button[kind="primary"]{
  background: linear-gradient(180deg, var(--brand) 0%, #3D6FFF 100%) !important;
  border: 1px solid rgba(91,140,255,0.35) !important;
}
button[kind="secondary"]{
  background: rgba(14,20,38,0.75) !important;
  border: 1px solid var(--line) !important;
  color: var(--text) !important;
}

/* Dataframe container */
[data-testid="stDataFrame"]{
  background: rgba(8,11,20,0.55) !important;
  border: 1px solid var(--line) !important;
  border-radius: 14px !important;
  overflow: hidden;
}
[data-testid="stDataFrame"] *{
  color: var(--text) !important;
}

/* Alerts */
div[data-testid="stAlert"]{
  border-radius: 14px !important;
  border-color: var(--line) !important;
}

/* Progress */
.stProgress > div{
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid var(--line) !important;
  border-radius: 999px !important;
}
.stProgress > div > div > div > div{
  border-radius: 999px !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==============================
# 🧠 Estado (somente chaves pequenas)
# ==============================
def _ensure_state():
    ss = st.session_state
    ss.setdefault("view", "single")            # single | batch
    ss.setdefault("single_mode", "txt")        # txt | wav
    ss.setdefault("batch_mode", "txt")         # txt | wav
    ss.setdefault("processing", False)

    # IDs pequenos (resultados grandes ficam fora da sessão)
    ss.setdefault("single_result_id", "")
    ss.setdefault("batch_result_id", "")

    # Estimativas (leves)
    ss.setdefault("ema_txt_sec", None)
    ss.setdefault("ema_wav_sec", None)
    ss.setdefault("ema_batch_item_sec", None)

_ensure_state()


# ==============================
# 🧺 Store em memória (fora do session_state)
# ==============================
_STORE: Dict[str, Dict[str, Any]] = {}
_STORE_ORDER: List[str] = []
_STORE_MAX = 40

def _store_put(payload: Dict[str, Any]) -> str:
    sid = uuid.uuid4().hex
    _STORE[sid] = payload
    _STORE_ORDER.append(sid)
    while len(_STORE_ORDER) > _STORE_MAX:
        old = _STORE_ORDER.pop(0)
        _STORE.pop(old, None)
    return sid

def _store_get(sid: str) -> Optional[Dict[str, Any]]:
    if not sid:
        return None
    return _STORE.get(sid)

def _store_del(sid: str) -> None:
    if not sid:
        return
    _STORE.pop(sid, None)
    try:
        _STORE_ORDER.remove(sid)
    except ValueError:
        pass

def clear_single():
    _store_del(st.session_state.get("single_result_id", ""))
    st.session_state["single_result_id"] = ""

def clear_batch():
    _store_del(st.session_state.get("batch_result_id", ""))
    st.session_state["batch_result_id"] = ""

def clear_all():
    clear_single()
    clear_batch()


# ==============================
# ✅ Validação (cliente-friendly)
# ==============================
def validar_transcricao(txt: str) -> Tuple[bool, str]:
    linhas = [l.strip() for l in (txt or "").splitlines() if l.strip()]
    if len(linhas) < 4:
        return False, "O texto está muito curto para análise. Cole uma conversa completa."
    if not any(re.match(r"^\[(VENDEDOR|CLIENTE)\]", l, re.I) for l in linhas):
        return False, "Use o formato com [VENDEDOR] e [CLIENTE] no início de cada fala."
    return True, "ok"


# ==============================
# ⏱️ Utilidades
# ==============================
def duracao_wav_seg_bytes(wav_bytes: bytes) -> float:
    try:
        bio = io.BytesIO(wav_bytes)
        with wave.open(bio, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0

def human_time(sec: float) -> str:
    try:
        sec = float(sec)
    except Exception:
        sec = 0.0
    sec = max(0.0, sec)
    if sec < 60:
        return f"{int(sec)}s"
    return f"{int(sec // 60)}m {int(sec % 60)}s"


# ==============================
# 📏 Excel: formatação leve
# ==============================
from io import BytesIO

def format_excel_bytes(excel_bytes: bytes) -> bytes:
    if not excel_bytes:
        return excel_bytes
    try:
        from openpyxl import load_workbook
        from openpyxl.styles import Alignment
    except Exception:
        return excel_bytes

    bio = BytesIO(excel_bytes)
    wb = load_workbook(bio)
    ws = wb.active
    ws.freeze_panes = "A2"

    long_text_markers = ("_texto", "_feedback", "justific", "trecho", "observ", "coment", "resumo", "explic")
    headers = {}
    for col_idx in range(1, ws.max_column + 1):
        v = ws.cell(row=1, column=col_idx).value
        if v is not None:
            headers[str(v)] = col_idx

    wrap_align = Alignment(wrap_text=True, vertical="top", horizontal="left")
    normal_align = Alignment(wrap_text=False, vertical="top", horizontal="left")
    max_rows = min(ws.max_row, 5000)

    for header, col_idx in headers.items():
        h = str(header).lower()
        is_long = any(m in h for m in long_text_markers)
        col_letter = ws.cell(row=1, column=col_idx).column_letter
        ws.column_dimensions[col_letter].width = min(
            EXCEL_TEXT_COL_W if is_long else EXCEL_DEFAULT_COL_W,
            EXCEL_MAX_COL_W,
        )
        if EXCEL_WRAP_TEXT:
            for r in range(1, max_rows + 1):
                cell = ws.cell(row=r, column=col_idx)
                cell.alignment = wrap_align if is_long else normal_align

    ws.row_dimensions[1].height = 22
    out = BytesIO()
    wb.save(out)
    return out.getvalue()

def excel_bytes_to_df(excel_bytes: bytes) -> pd.DataFrame:
    bio = io.BytesIO(excel_bytes)
    return pd.read_excel(bio)

def _safe_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    ren = {"filename": "arquivo", "file": "arquivo"}
    for k, v in ren.items():
        if k in df.columns and v not in df.columns:
            df.rename(columns={k: v}, inplace=True)
    if "arquivo" not in df.columns:
        df["arquivo"] = ""
    return df


# ==============================
# 🌐 Conectividade (discreta)
# ==============================
@st.cache_data(ttl=10)
def _health_cached(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=(3, 6))
        return r.status_code == 200
    except Exception:
        return False

def service_ok() -> bool:
    if st.session_state.get("processing"):
        return True
    return _health_cached(BASE_URL)


# ==============================
# 🌐 Chamada principal
# ==============================
def run_remote_file(file_bytes: bytes, filename: str, mime: str) -> Tuple[bytes, str]:
    files = {"file": (filename, file_bytes, mime)}
    headers = {"X-API-KEY": API_KEY}
    r = requests.post(
        f"{BASE_URL}/run",
        files=files,
        headers=headers,
        timeout=REQ_TIMEOUT,
    )
    r.raise_for_status()
    run_id = r.headers.get("X-Run-Id", "") or ""
    return r.content, run_id


# ==============================
# 📦 ZIP helpers
# ==============================
def zip_extract_all(zip_bytes: bytes) -> Dict[str, bytes]:
    out: Dict[str, bytes] = {}
    bio = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(bio, "r") as z:
        for name in z.namelist():
            try:
                out[name] = z.read(name)
            except Exception:
                pass
    return out

def pick_excels(files_map: Dict[str, bytes]) -> List[Tuple[str, bytes]]:
    excels = [(k, v) for k, v in files_map.items() if k.lower().endswith(".xlsx")]
    if not excels:
        return []

    def _score(name: str) -> int:
        n = name.lower()
        if "spin_resultados_lote" in n:
            return 0
        if n.endswith("_spin.xlsx") or "_spin" in n:
            return 1
        return 2

    excels.sort(key=lambda kv: (_score(kv[0]), kv[0]))
    return excels


# ==============================
# ⏳ Progresso (estilo antigo, dark)
# ==============================
def run_with_progress(
    phases: List[Tuple[str, float]],
    target_func,
    estimate_total_sec: Optional[float] = None,
):
    st.session_state["processing"] = True

    box = st.container()
    with box:
        st.markdown(
            """
<div class="card">
  <p class="kicker">Em andamento</p>
  <p class="title">Processando sua avaliação</p>
  <p class="smallmuted" style="margin-top:8px;">Acompanhe o progresso abaixo.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        status_line = st.empty()
        pbar = st.progress(0)
        timer_line = st.empty()

    result_holder = {"ok": False, "value": None, "error": None}
    t0 = time.time()

    def _worker():
        try:
            val = target_func()
            result_holder["ok"] = True
            result_holder["value"] = val
        except Exception as e:
            result_holder["error"] = e

    th = threading.Thread(target=_worker, daemon=True)
    th.start()

    last_msg = ""
    while th.is_alive():
        elapsed = time.time() - t0

        if estimate_total_sec and estimate_total_sec > 2:
            p = min(0.92, elapsed / max(estimate_total_sec, 1.0))
        else:
            p = min(0.85, elapsed / 150.0)

        pbar.progress(max(0.01, float(p)))

        frac = min(0.999, p / 0.92)
        idx = 0
        for i, (_, w) in enumerate(phases):
            if frac <= w:
                idx = i
                break
        msg = phases[idx][0] if phases else "Processando…"
        if msg != last_msg:
            status_line.markdown(f"<div class='card-tight'><span class='smallmuted'>• {msg}</span></div>", unsafe_allow_html=True)
            last_msg = msg

        timer_line.markdown(
            f"<div class='card-tight'><span class='smallmuted'>⏱️ Tempo decorrido: <b>{human_time(elapsed)}</b></span></div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.15)

    elapsed = time.time() - t0
    pbar.progress(1.0)
    time.sleep(0.05)
    box.empty()

    st.session_state["processing"] = False

    if not result_holder["ok"]:
        raise result_holder["error"]

    return result_holder["value"], float(elapsed)


def _ema_update(key: str, x: float, alpha: float = 0.25):
    old = st.session_state.get(key)
    if old is None:
        st.session_state[key] = float(x)
    else:
        st.session_state[key] = float(alpha * x + (1 - alpha) * float(old))


# ==============================
# ✅ Execução: Individual
# ==============================
def run_single_txt(txt: str):
    ok, msg = validar_transcricao(txt)
    if not ok:
        st.warning(msg)
        return

    fname = f"avaliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    est = st.session_state.get("ema_txt_sec")

    phases = [
        ("Preparando…", 0.15),
        ("Enviando…", 0.30),
        ("Analisando…", 0.85),
        ("Gerando planilha…", 0.97),
        ("Finalizando…", 1.00),
    ]

    def _do():
        zip_bytes, run_id = run_remote_file(txt.encode("utf-8", errors="ignore"), fname, "text/plain")
        return zip_bytes, run_id

    try:
        (zip_bytes, run_id), elapsed = run_with_progress(phases, _do, estimate_total_sec=est)
    except Exception:
        st.error("Não foi possível concluir agora. Tente novamente em instantes.")
        return

    _ema_update("ema_txt_sec", elapsed)

    files_map = zip_extract_all(zip_bytes)
    excels = pick_excels(files_map)
    if not excels:
        st.error("Concluí a execução, mas não encontrei a planilha. Tente novamente.")
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)
    try:
        df = _safe_df(excel_bytes_to_df(main_xlsx_fmt))
    except Exception:
        df = pd.DataFrame()

    clear_single()
    st.session_state["single_result_id"] = _store_put(
        {
            "type": "single",
            "kind": "txt",
            "run_id": run_id,
            "source_name": fname,
            "excel_name": main_name,
            "excel_bytes": main_xlsx_fmt,
            "df": df,
            "timings": {"audio_sec": 0.0, "total_sec": float(elapsed)},
            "created_at": time.time(),
        }
    )


def run_single_wav(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()
    audio_sec = duracao_wav_seg_bytes(wav_bytes)

    est = st.session_state.get("ema_wav_sec")

    phases = [
        ("Preparando…", 0.15),
        ("Enviando…", 0.30),
        ("Processando áudio…", 0.75),
        ("Analisando…", 0.90),
        ("Gerando planilha…", 0.97),
        ("Finalizando…", 1.00),
    ]

    def _do():
        zip_bytes, run_id = run_remote_file(wav_bytes, wav_file.name, "audio/wav")
        return zip_bytes, run_id

    try:
        (zip_bytes, run_id), elapsed = run_with_progress(phases, _do, estimate_total_sec=est)
    except Exception:
        st.error("Não foi possível concluir agora. Tente novamente em instantes.")
        return

    _ema_update("ema_wav_sec", elapsed)

    files_map = zip_extract_all(zip_bytes)
    excels = pick_excels(files_map)
    if not excels:
        st.error("Concluí a execução, mas não encontrei a planilha. Tente novamente.")
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)
    try:
        df = _safe_df(excel_bytes_to_df(main_xlsx_fmt))
    except Exception:
        df = pd.DataFrame()

    clear_single()
    st.session_state["single_result_id"] = _store_put(
        {
            "type": "single",
            "kind": "wav",
            "run_id": run_id,
            "source_name": wav_file.name,
            "excel_name": main_name,
            "excel_bytes": main_xlsx_fmt,
            "df": df,
            "timings": {"audio_sec": float(audio_sec or 0.0), "total_sec": float(elapsed)},
            "created_at": time.time(),
        }
    )


# ==============================
# ✅ Execução: Lote (limites)
# ==============================
MAX_BATCH_WAV_FILES = 5
MAX_BATCH_WAV_SECONDS = 600
MAX_BATCH_TXT_ENTRIES = 8

def render_batch_limits(mode: str):
    if mode == "wav":
        st.markdown(
            f"""
<div class="card-tight">
  <p class="smallmuted" style="margin:0;">
    <span class="badge warn">Limites do lote</span>
    <span class="badge">Áudio: até {MAX_BATCH_WAV_FILES} arquivos</span>
    <span class="badge">até 10 minutos cada</span>
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
<div class="card-tight">
  <p class="smallmuted" style="margin:0;">
    <span class="badge warn">Limites do lote</span>
    <span class="badge">Texto: até {MAX_BATCH_TXT_ENTRIES} entradas</span>
    <span class="badge">arquivos + blocos colados</span>
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

def run_batch_txt(files: List[Any], pasted_blocks: List[str]):
    entradas: List[Tuple[str, str]] = []

    if files:
        for f in files:
            if len(entradas) >= MAX_BATCH_TXT_ENTRIES:
                break
            entradas.append((f.name, f.getvalue().decode("utf-8", errors="ignore")))

    if pasted_blocks:
        for i, b in enumerate(pasted_blocks, start=1):
            if len(entradas) >= MAX_BATCH_TXT_ENTRIES:
                break
            entradas.append((f"colado_{i}.txt", b))

    if not entradas:
        st.warning("Envie textos ou cole pelo menos um bloco.")
        return

    if len(entradas) > MAX_BATCH_TXT_ENTRIES:
        st.warning(f"No lote, use até {MAX_BATCH_TXT_ENTRIES} entradas no total.")
        return

    for name, txt in entradas:
        ok, msg = validar_transcricao(txt)
        if not ok:
            st.warning(f"• {name}: {msg}")
            return

    est_item = st.session_state.get("ema_batch_item_sec")
    est_total = (est_item * len(entradas)) if est_item else None

    phases = [
        ("Preparando lote…", 0.20),
        ("Enviando itens…", 0.35),
        ("Analisando…", 0.90),
        ("Consolidando…", 0.98),
        ("Finalizando…", 1.00),
    ]

    def _do():
        itens: List[dict] = []
        lote_excel_payload = None

        for idx, (name, txt) in enumerate(entradas, start=1):
            zip_bytes, run_id = run_remote_file(txt.encode("utf-8", errors="ignore"), name, "text/plain")
            files_map = zip_extract_all(zip_bytes)
            excels = pick_excels(files_map)

            chosen = None
            for nm, xb in excels:
                if nm.lower().endswith("_spin.xlsx") or "_spin" in nm.lower():
                    chosen = (nm, xb)
                    break
            if not chosen and excels:
                chosen = excels[0]

            indiv_name, indiv_xlsx_fmt = "", b""
            if chosen:
                indiv_name, indiv_xlsx = chosen
                indiv_xlsx_fmt = format_excel_bytes(indiv_xlsx)

            itens.append(
                {
                    "idx": idx,
                    "filename": name,
                    "run_id": run_id,
                    "excel_individual_name": indiv_name,
                    "excel_individual_bytes": indiv_xlsx_fmt,
                }
            )

            for nm, xb in excels:
                if "spin_resultados_lote" in nm.lower():
                    lote_excel_payload = (nm, format_excel_bytes(xb))
                    break

        return itens, lote_excel_payload

    try:
        (itens, lote_excel_payload), elapsed = run_with_progress(phases, _do, estimate_total_sec=est_total)
    except Exception:
        st.error("Não foi possível concluir o lote agora. Tente novamente em instantes.")
        return

    if len(entradas) > 0:
        _ema_update("ema_batch_item_sec", elapsed / max(1, len(entradas)))

    lote_df = pd.DataFrame()
    lote_name = ""
    lote_bytes = b""
    if lote_excel_payload:
        lote_name, lote_bytes = lote_excel_payload
        try:
            lote_df = _safe_df(excel_bytes_to_df(lote_bytes))
        except Exception:
            lote_df = pd.DataFrame()

    clear_batch()
    st.session_state["batch_result_id"] = _store_put(
        {
            "type": "batch",
            "kind": "txt",
            "count": len(entradas),
            "created_at": time.time(),
            "lote": {"excel_name": lote_name, "excel_bytes": lote_bytes, "df": lote_df},
            "items": itens,
            "timings": {"total_sec": float(elapsed)},
        }
    )

def run_batch_wav(wavs: List[Any]):
    if not wavs:
        st.warning("Envie pelo menos 1 áudio para continuar.")
        return

    if len(wavs) > MAX_BATCH_WAV_FILES:
        st.warning(f"No lote, envie até {MAX_BATCH_WAV_FILES} áudios.")
        return

    for wf in wavs:
        sec = duracao_wav_seg_bytes(wf.getbuffer().tobytes())
        if sec and sec > MAX_BATCH_WAV_SECONDS:
            st.warning(f"• {wf.name}: acima de 10 minutos. Ajuste o arquivo e tente novamente.")
            return

    est_item = st.session_state.get("ema_batch_item_sec")
    est_total = (est_item * len(wavs)) if est_item else None

    phases = [
        ("Preparando lote…", 0.20),
        ("Enviando itens…", 0.35),
        ("Processando áudio…", 0.88),
        ("Consolidando…", 0.98),
        ("Finalizando…", 1.00),
    ]

    def _do():
        itens: List[dict] = []
        lote_excel_payload = None

        for idx, wavf in enumerate(wavs, start=1):
            wav_bytes = wavf.getbuffer().tobytes()
            zip_bytes, run_id = run_remote_file(wav_bytes, wavf.name, "audio/wav")
            files_map = zip_extract_all(zip_bytes)
            excels = pick_excels(files_map)

            chosen = None
            for nm, xb in excels:
                if nm.lower().endswith("_spin.xlsx") or "_spin" in nm.lower():
                    chosen = (nm, xb)
                    break
            if not chosen and excels:
                chosen = excels[0]

            indiv_name, indiv_xlsx_fmt = "", b""
            if chosen:
                indiv_name, indiv_xlsx = chosen
                indiv_xlsx_fmt = format_excel_bytes(indiv_xlsx)

            itens.append(
                {
                    "idx": idx,
                    "filename": wavf.name,
                    "run_id": run_id,
                    "excel_individual_name": indiv_name,
                    "excel_individual_bytes": indiv_xlsx_fmt,
                }
            )

            for nm, xb in excels:
                if "spin_resultados_lote" in nm.lower():
                    lote_excel_payload = (nm, format_excel_bytes(xb))
                    break

        return itens, lote_excel_payload

    try:
        (itens, lote_excel_payload), elapsed = run_with_progress(phases, _do, estimate_total_sec=est_total)
    except Exception:
        st.error("Não foi possível concluir o lote agora. Tente novamente em instantes.")
        return

    if len(wavs) > 0:
        _ema_update("ema_batch_item_sec", elapsed / max(1, len(wavs)))

    lote_df = pd.DataFrame()
    lote_name = ""
    lote_bytes = b""
    if lote_excel_payload:
        lote_name, lote_bytes = lote_excel_payload
        try:
            lote_df = _safe_df(excel_bytes_to_df(lote_bytes))
        except Exception:
            lote_df = pd.DataFrame()

    clear_batch()
    st.session_state["batch_result_id"] = _store_put(
        {
            "type": "batch",
            "kind": "wav",
            "count": len(wavs),
            "created_at": time.time(),
            "lote": {"excel_name": lote_name, "excel_bytes": lote_bytes, "df": lote_df},
            "items": itens,
            "timings": {"total_sec": float(elapsed)},
        }
    )


# ==============================
# 🧠 Header (padrão antigo, dark)
# ==============================
st.markdown("## 🎧 SPIN Analyzer — Avaliação de Ligações")
st.markdown("<div class='smallmuted'>Relatórios automáticos com base no método <b>SPIN Selling</b>.</div>", unsafe_allow_html=True)
st.markdown("---")


# ==============================
# 🧭 Sidebar (sem técnica)
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")
    disabled = st.session_state.get("processing", False)

    if st.button("👤 Avaliação Individual", use_container_width=True, disabled=disabled):
        if st.session_state["view"] != "single":
            clear_all()
        st.session_state["view"] = "single"
        st.rerun()

    if st.button("📊 Visão Gerencial", use_container_width=True, disabled=disabled):
        if st.session_state["view"] != "batch":
            clear_all()
        st.session_state["view"] = "batch"
        st.rerun()

    st.markdown("---")
    if service_ok():
        st.success("Conectado ✅")
    else:
        st.warning("Indisponível no momento ⚠️")

    st.markdown("---")
    if st.button("🧹 Limpar", use_container_width=True, disabled=disabled):
        clear_all()
        st.rerun()


# ==============================
# ✅ UI: Telas
# ==============================
if st.session_state["view"] == "single":
    st.markdown(
        """
<div class="card">
  <p class="kicker">Avaliação Individual</p>
  <p class="title">Envie um texto ou um áudio</p>
  <p class="smallmuted" style="margin-top:8px;">Ao concluir, você vê a planilha e pode baixar o Excel.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    single_mode = st.radio(
        "Entrada",
        options=["txt", "wav"],
        format_func=lambda x: "📝 Texto" if x == "txt" else "🎧 Áudio (WAV)",
        horizontal=True,
        key="radio_single_mode",
        disabled=st.session_state.get("processing", False),
    )

    if single_mode != st.session_state.get("single_mode"):
        clear_single()
        st.session_state["single_mode"] = single_mode

    if single_mode == "txt":
        st.markdown("<div class='smallmuted'>Use <b>[VENDEDOR]</b> e <b>[CLIENTE]</b> no início das falas.</div>", unsafe_allow_html=True)
        txt_input = st.text_area(
            "Cole a transcrição aqui",
            height=260,
            value="",
            key="txt_input_single",
            placeholder="[VENDEDOR] ...\n[CLIENTE] ...\n[VENDEDOR] ...",
            disabled=st.session_state.get("processing", False),
        )
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", type="primary", use_container_width=True, disabled=st.session_state.get("processing", False)):
                clear_single()
                run_single_txt(txt_input)
        with colB:
            if st.button("🧹 Limpar", use_container_width=True, disabled=st.session_state.get("processing", False)):
                clear_single()
                st.rerun()

    else:
        up_wav = st.file_uploader(
            "Envie um WAV",
            type=["wav"],
            accept_multiple_files=False,
            key="uploader_wav_single",
            disabled=st.session_state.get("processing", False),
        )
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", type="primary", use_container_width=True, disabled=st.session_state.get("processing", False)):
                if up_wav is None:
                    st.warning("Envie um WAV para continuar.")
                else:
                    clear_single()
                    run_single_wav(up_wav)
        with colB:
            if st.button("🧹 Limpar", use_container_width=True, disabled=st.session_state.get("processing", False)):
                clear_single()
                st.rerun()

else:
    st.markdown(
        """
<div class="card">
  <p class="kicker">Visão Gerencial</p>
  <p class="title">Analise vários itens de uma vez</p>
  <p class="smallmuted" style="margin-top:8px;">Ao concluir, você recebe um Excel consolidado e uma planilha por item.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    batch_mode = st.radio(
        "Entrada",
        options=["txt", "wav"],
        format_func=lambda x: "📝 Texto" if x == "txt" else "🎧 Áudio (WAV)",
        horizontal=True,
        key="radio_batch_mode",
        disabled=st.session_state.get("processing", False),
    )

    if batch_mode != st.session_state.get("batch_mode"):
        clear_batch()
        st.session_state["batch_mode"] = batch_mode

    render_batch_limits(batch_mode)

    if batch_mode == "txt":
        st.markdown("<div class='smallmuted'>Textos com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b> no início das falas.</div>", unsafe_allow_html=True)
        up_txts = st.file_uploader(
            "Envie TXT(s)",
            type=["txt"],
            accept_multiple_files=True,
            key="uploader_txt_batch",
            disabled=st.session_state.get("processing", False),
        )
        st.markdown("<div class='smallmuted'>Ou cole blocos separados por uma linha contendo <b>---</b></div>", unsafe_allow_html=True)
        multi_txt = st.text_area(
            "Cole aqui (separe com ---)",
            height=220,
            value="",
            key="txt_input_batch",
            placeholder="[VENDEDOR] ...\n[CLIENTE] ...\n---\n[VENDEDOR] ...\n[CLIENTE] ...",
            disabled=st.session_state.get("processing", False),
        )
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar lote", type="primary", use_container_width=True, disabled=st.session_state.get("processing", False)):
                blocks = []
                if multi_txt.strip():
                    blocks = [b.strip() for b in multi_txt.split("\n---\n") if b.strip()]
                clear_batch()
                run_batch_txt(up_txts or [], blocks)
        with colB:
            if st.button("🧹 Limpar", use_container_width=True, disabled=st.session_state.get("processing", False)):
                clear_batch()
                st.rerun()

    else:
        up_wavs = st.file_uploader(
            "Envie WAV(s)",
            type=["wav"],
            accept_multiple_files=True,
            key="uploader_wav_batch",
            disabled=st.session_state.get("processing", False),
        )
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar lote", type="primary", use_container_width=True, disabled=st.session_state.get("processing", False)):
                clear_batch()
                run_batch_wav(up_wavs or [])
        with colB:
            if st.button("🧹 Limpar", use_container_width=True, disabled=st.session_state.get("processing", False)):
                clear_batch()
                st.rerun()


# ==============================
# ✅ RESULTADOS
# ==============================
single_payload = _store_get(st.session_state.get("single_result_id", ""))
if single_payload and single_payload.get("type") == "single":
    st.markdown("---")
    st.markdown("## ✅ Resultado")

    kind = single_payload.get("kind", "")
    run_id = single_payload.get("run_id", "")
    src = single_payload.get("source_name", "")

    badges = []
    badges.append("<span class='badge ok'>📝 Texto</span>" if kind == "txt" else "<span class='badge ok'>🎧 Áudio</span>")
    if src:
        badges.append(f"<span class='badge'>Arquivo: {Path(src).name}</span>")
    if run_id:
        badges.append(f"<span class='badge brand'>Protocolo: {run_id}</span>")

    st.markdown(f"<div class='card'><div class='badges'>{''.join(badges)}</div></div>", unsafe_allow_html=True)

    df = single_payload.get("df", pd.DataFrame())
    st.markdown("<div class='card'><p class='section-title'>📊 Planilha</p><p class='smallmuted'>Visualização para consulta rápida.</p></div>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)

    timings = single_payload.get("timings", {}) or {}
    audio_sec = float(timings.get("audio_sec", 0) or 0)
    total_sec = float(timings.get("total_sec", 0) or 0)

    st.markdown(
        f"""
<div class="card">
  <p class="section-title">⏱️ Tempo</p>
  <div class="badges">
    <span class="badge">Duração: <b>{human_time(audio_sec)}</b></span>
    <span class="badge">Processamento: <b>{human_time(total_sec)}</b></span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="card">
  <p class="section-title">📥 Download</p>
  <p class="smallmuted" style="margin-top:8px;">Baixe a planilha pronta para abrir no Excel.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    base = Path(single_payload.get("source_name") or "avaliacao").stem
    excel_bytes = single_payload.get("excel_bytes", b"")
    st.download_button(
        "📥 Baixar Excel",
        data=excel_bytes,
        file_name=f"{base}_avaliacao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"dl_single_excel_{base}_{single_payload.get('created_at',0)}",
    )


batch_payload = _store_get(st.session_state.get("batch_result_id", ""))
if batch_payload and batch_payload.get("type") == "batch":
    st.markdown("---")
    st.markdown("## ✅ Resultados do lote")

    lote = batch_payload.get("lote", {}) or {}
    lote_df = lote.get("df", pd.DataFrame())
    lote_bytes = lote.get("excel_bytes", b"")

    st.markdown("<div class='card'><p class='section-title'>📊 Consolidado</p><p class='smallmuted'>Resumo do lote em uma única planilha.</p></div>", unsafe_allow_html=True)
    if isinstance(lote_df, pd.DataFrame) and not lote_df.empty:
        st.dataframe(lote_df, use_container_width=True)
    else:
        st.info("O consolidado está disponível para download.")

    st.markdown(
        """
<div class="card">
  <p class="section-title">📥 Downloads</p>
  <p class="smallmuted" style="margin-top:8px;">
    <b>Excel do lote</b> consolida todos os itens.<br/>
    <b>Excel individual</b> é uma planilha separada por item.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    if lote_bytes:
        st.download_button(
            "📥 Baixar Excel do lote",
            data=lote_bytes,
            file_name=f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_lote_excel_{batch_payload.get('created_at',0)}",
        )

    items = batch_payload.get("items", []) or []
    st.markdown("<div class='card'><p class='section-title'>📁 Itens</p><p class='smallmuted'>Abra um item para baixar a planilha individual.</p></div>", unsafe_allow_html=True)

    for item in items:
        idx = item.get("idx", 0)
        filename = str(item.get("filename") or f"item_{idx}")
        base = Path(filename).stem
        with st.expander(f"{idx}. {filename}", expanded=False):
            xb = item.get("excel_individual_bytes", b"") or b""
            if xb:
                st.download_button(
                    "📥 Baixar Excel (individual)",
                    data=xb,
                    file_name=f"{base}_avaliacao.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_item_excel_{idx}_{base}_{batch_payload.get('created_at',0)}",
                )
            else:
                st.info("Planilha individual não disponível para este item.")


# ==============================
# 🧾 Rodapé
# ==============================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#A9B4CC;font-weight:700;'>SPIN Analyzer — Projeto Tele_IA 2026</div>",
    unsafe_allow_html=True,
)
