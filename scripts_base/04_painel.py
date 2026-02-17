# ===============================================
# 🎧 SPIN Analyzer — Painel (Texto + Áudio)
# ✅ Saída: SOMENTE PLANILHAS (Excel) — sem TXT
# ✅ Individual: abre Excel principal + download
# ✅ Gerencial (lote): abre Excel consolidado + downloads (lote + por item)
# ✅ UX: foco total no cliente (sem termos técnicos), visual premium, progresso com tempo decorrido
# ✅ Bugfix robusto: session_state leve (sem ZIP, sem mapas de arquivos)
# ✅ Limites (lote): Áudio até 5 arquivos e 10 min cada | Texto até 8 entradas
# ===============================================

import os
import re
import io
import time
import zipfile
import wave
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
# 🔐 Configurações (Secrets/Env)
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
VPS_BASE_URL = _get_cfg("VPS_BASE_URL", "").rstrip("/")
VPS_API_KEY = _get_cfg("VPS_API_KEY", "")

CONNECT_TIMEOUT_S = int(_get_cfg("CONNECT_TIMEOUT_S", "10"))
READ_TIMEOUT_S = int(_get_cfg("API_TIMEOUT_S", "7200"))
REQ_TIMEOUT = (CONNECT_TIMEOUT_S, READ_TIMEOUT_S)

EXCEL_WRAP_TEXT = _get_cfg("EXCEL_WRAP_TEXT", "1").strip() not in ("0", "false", "False", "")
EXCEL_DEFAULT_COL_W = int(_get_cfg("EXCEL_DEFAULT_COL_W", "22"))
EXCEL_TEXT_COL_W = int(_get_cfg("EXCEL_TEXT_COL_W", "55"))
EXCEL_MAX_COL_W = int(_get_cfg("EXCEL_MAX_COL_W", "80"))

# Limites (obrigatórios)
BATCH_WAV_MAX_FILES = 5
BATCH_WAV_MAX_SECONDS_EACH = 10 * 60
BATCH_TEXT_MAX_ENTRIES = 8

if MODE != "VPS":
    st.error("Este painel está configurado para funcionar apenas no modo online. Verifique as configurações do projeto.")
    st.stop()
if not VPS_BASE_URL:
    st.error("Configuração ausente: endereço do serviço de avaliação.")
    st.stop()
if not VPS_API_KEY:
    st.error("Configuração ausente: chave de acesso do serviço de avaliação.")
    st.stop()


# ==============================
# 🎨 Estilo premium (limpo e consistente)
# ==============================
st.markdown(
    """
<style>
/* Base */
body { background-color:#FFFFFF; color:#0B1220; font-family:Segoe UI, Arial, sans-serif; }
h1, h2, h3 { color:#0B63F3; }

/* Ajustes gerais */
.block-container { padding-top: 1.2rem; padding-bottom: 2.0rem; }
div[data-testid="stAlert"] { border-radius: 14px; }

/* Cards */
.card{
  background:#FFFFFF !important;
  color:#0B1220 !important;
  border:1px solid rgba(199,214,245,0.95) !important;
  border-radius:18px;
  padding:18px;
  margin-bottom:14px;
  box-shadow:0 10px 28px rgba(11,18,32,0.08);
}
.card *{ color:#0B1220 !important; }

.smallmuted{ color:#3A4A63; font-weight:650; }
.mini{ font-size:0.92rem; }

/* Pills */
.pill-row{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; justify-content:flex-end; }
.pill{
  display:inline-flex; align-items:center; gap:8px;
  padding:8px 12px; border-radius:999px;
  border:1px solid #AFC7F3; background:#F6F9FF;
  color:#0B63F3; font-weight:800; font-size:0.92rem; line-height:1;
}
.pill .dot{ width:9px; height:9px; border-radius:999px; background:#0B63F3; display:inline-block; }
.pill.ok{ background:#E6FFF3; border-color:#29B37C; color:#0B6B4B; }
.pill.ok .dot{ background:#29B37C; }
.pill.warn{ background:#FFF8E6; border-color:#F0C36D; color:#7A4E00; }
.pill.warn .dot{ background:#F0C36D; }

/* Hero */
.hero{
  display:flex; align-items:flex-start; justify-content:space-between; gap:14px;
  padding:18px; border-radius:22px;
  border:1px solid rgba(199,214,245,0.85);
  background:linear-gradient(135deg, rgba(246,249,255,1) 0%, rgba(255,255,255,1) 55%, rgba(230,255,243,0.65) 100%);
  box-shadow:0 14px 34px rgba(11,18,32,0.10);
  margin-top:8px; margin-bottom:14px;
}
.hero .left{ display:flex; gap:12px; align-items:flex-start; }
.hero .icon{
  width:42px; height:42px; border-radius:14px;
  background:#E6FFF3; border:1px solid #29B37C;
  display:flex; align-items:center; justify-content:center; font-size:22px;
}
.hero .title{ margin:0; font-size:1.45rem; font-weight:900; color:#0B1220; }
.hero .subtitle{ margin:6px 0 0 0; color:#3A4A63; font-weight:650; }

/* Status (progresso) */
.status-card{
  background:linear-gradient(135deg, #FFFFFF 0%, #F6F9FF 55%, #FFFFFF 100%) !important;
  border:1px solid rgba(199,214,245,0.95) !important;
  border-radius:18px !important;
  padding:16px 18px !important;
  box-shadow:0 12px 30px rgba(11,18,32,0.08);
}
.status-title{ margin:0 !important; font-size:1.10rem !important; font-weight:900 !important; color:#0B1220 !important; }
.status-sub{ margin:6px 0 0 0 !important; color:#3A4A63 !important; font-weight:650 !important; }

/* “Cabeçalho” da área */
.section-title{
  margin: 0 0 6px 0;
  font-size: 1.05rem;
  font-weight: 900;
  color:#0B1220;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==============================
# 🧠 Estado do app (LEVE)
# ==============================
def _ensure_state():
    st.session_state.setdefault("view", "single")             # single | batch
    st.session_state.setdefault("single_mode", "Texto")       # Texto | Áudio
    st.session_state.setdefault("batch_mode", "Texto")        # Texto | Áudio

    st.session_state.setdefault("last_result", None)          # dict leve
    st.session_state.setdefault("batch_results", None)        # list[dict] leve
    st.session_state.setdefault("batch_lote", None)           # dict leve
    st.session_state.setdefault("last_run_id", "")

    st.session_state.setdefault("_prev_view", st.session_state["view"])
    st.session_state.setdefault("_prev_single_mode", st.session_state["single_mode"])
    st.session_state.setdefault("_prev_batch_mode", st.session_state["batch_mode"])


_ensure_state()


def clear_all_results():
    st.session_state["last_result"] = None
    st.session_state["batch_results"] = None
    st.session_state["batch_lote"] = None
    st.session_state["last_run_id"] = ""


def clear_single():
    st.session_state["last_result"] = None
    st.session_state["last_run_id"] = ""


def clear_batch():
    st.session_state["batch_results"] = None
    st.session_state["batch_lote"] = None
    st.session_state["last_run_id"] = ""


# ==============================
# ✅ Validação do texto
# ==============================
def validar_transcricao(txt: str) -> Tuple[bool, str]:
    linhas = [l.strip() for l in (txt or "").splitlines() if l.strip()]
    if len(linhas) < 4:
        return False, "O conteúdo está muito curto para avaliação."
    if not any(re.match(r"^\[(VENDEDOR|CLIENTE)\]", l, re.I) for l in linhas):
        return False, "Formato inválido. Comece as falas com [VENDEDOR] e [CLIENTE]."
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
    if sec < 60:
        return f"{int(sec)}s"
    return f"{int(sec // 60)}m {int(sec % 60)}s"


# ==============================
# 📏 Excel: formatar largura + wrap text
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
# 🌐 Serviço remoto (sem termos técnicos na UI)
# ==============================
def vps_health() -> bool:
    try:
        r = requests.get(f"{VPS_BASE_URL}/health", timeout=(3, 6))
        return r.status_code == 200
    except Exception:
        return False


def vps_run_file(
    file_bytes: bytes,
    filename: str,
    mime: str,
    status_cb=None,
) -> Tuple[bytes, Dict[str, str], float]:
    files = {"file": (filename, file_bytes, mime)}
    headers = {"X-API-KEY": VPS_API_KEY}

    t0 = time.time()

    try:
        if status_cb:
            status_cb("Preparando…", 12, None)

        r = requests.post(
            f"{VPS_BASE_URL}/run",
            files=files,
            headers=headers,
            timeout=REQ_TIMEOUT,
        )

        if status_cb:
            status_cb("Finalizando…", 92, None)

        r.raise_for_status()

        zip_bytes = r.content
        useful = {"X-Run-Id": r.headers.get("X-Run-Id", "")}
        return zip_bytes, useful, (time.time() - t0)

    except requests.exceptions.ConnectTimeout as e:
        raise RuntimeError("Não foi possível iniciar a avaliação agora. Tente novamente em instantes.") from e
    except requests.exceptions.ReadTimeout as e:
        raise RuntimeError("A avaliação está demorando além do esperado. Tente um arquivo menor.") from e
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError("Não foi possível acessar o serviço de avaliação no momento.") from e
    except requests.exceptions.HTTPError as e:
        code = getattr(r, "status_code", "—")
        raise RuntimeError(f"Não foi possível concluir a avaliação (código {code}).") from e
    except Exception as e:
        raise RuntimeError("Ocorreu um erro inesperado durante a avaliação.") from e


# ==============================
# 📦 ZIP helpers (somente local)
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


def summarize_excel_presence(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "Não foi possível abrir a planilha gerada."

    cols = [str(c).strip() for c in df.columns]
    phase_cols = [c for c in cols if c.lower().startswith("check_") or re.match(r"^p[0-4]", c.lower())]
    if not phase_cols:
        return "Planilha gerada com sucesso. Use as colunas exibidas para interpretar o resultado."

    try:
        dfn = df[phase_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        total = float(dfn.sum().sum())
        if total == 0.0:
            return (
                "As fases aparecem na planilha, mas os valores estão zerados neste arquivo. "
                "Isso pode acontecer quando o conteúdo está curto ou quando não há trechos claros das etapas."
            )
        return "As fases aparecem na planilha. Revise as colunas e valide com a conversa quando necessário."
    except Exception:
        return "As colunas de fases aparecem na planilha, mas não foi possível interpretar automaticamente os valores. Você pode revisar manualmente."


# ==============================
# 🧩 UI helpers
# ==============================
def render_hero(title: str, subtitle: str, pills: List[str], icon: str = "✅"):
    pill_html = "".join(pills)
    st.markdown(
        f"""
<div class="hero">
  <div class="left">
    <div class="icon">{icon}</div>
    <div>
      <p class="title">{title}</p>
      <p class="subtitle">{subtitle}</p>
    </div>
  </div>
  <div class="pill-row">
    {pill_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_time_card(audio_sec: float, total_sec: float):
    st.markdown(
        f"""
<div class="card">
  <div class="section-title">⏱️ Tempo</div>
  <p style="margin-top:10px;margin-bottom:0;">
    <span class="pill"><span class="dot"></span>Ligação <b>{human_time(audio_sec)}</b></span>
    &nbsp;&nbsp;
    <span class="pill"><span class="dot"></span>Processamento <b>{human_time(total_sec)}</b></span>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_downloads_explain():
    st.markdown(
        """
<div class="card">
  <div class="section-title">📥 Download</div>
  <p class="smallmuted" style="margin:8px 0 0 0;">
    Baixe a planilha pronta para abrir no Excel.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


# ==============================
# ⏳ Progresso (garantindo atualização)
# ==============================
def make_status_ui():
    status = st.empty()
    pbar = st.progress(0)   # 0..100 (inteiro)
    timer = st.empty()
    t0 = time.time()

    def _flush():
        # Ajuda o front a renderizar antes/entre etapas bloqueantes
        time.sleep(0.02)

    def update(msg: str, percent: int, _est_sec: Optional[float]):
        percent = int(max(0, min(100, percent)))
        elapsed = time.time() - t0

        timer.markdown(
            f"<div class='smallmuted'>⏳ Tempo decorrido: <b>{human_time(elapsed)}</b></div>",
            unsafe_allow_html=True,
        )
        status.markdown(
            f"""
<div class="status-card">
  <p class="status-title">{msg}</p>
  <p class="status-sub">Aguarde…</p>
</div>
""",
            unsafe_allow_html=True,
        )
        pbar.progress(percent)
        _flush()

    def done():
        status.empty()
        timer.empty()
        pbar.empty()

    return update, done


def show_friendly_error(title: str, err: Exception):
    st.error(title)
    with st.expander("Ver detalhes", expanded=False):
        st.code(str(err))


# ==============================
# ✅ Processamento: Individual
# ==============================
def run_single_text(content: str):
    ok, msg = validar_transcricao(content)
    if not ok:
        st.error(msg)
        return

    update, done = make_status_ui()
    update("Preparando…", 8, None)

    fname = f"avaliacao_texto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    try:
        update("Processando…", 22, None)
        zip_bytes, hdr, elapsed = vps_run_file(
            content.encode("utf-8", errors="ignore"),
            fname,
            "text/plain",
            status_cb=update,
        )
        update("Abrindo planilha…", 96, None)
    except Exception as e:
        done()
        show_friendly_error("Não foi possível concluir a avaliação.", e)
        return

    done()

    files_map = zip_extract_all(zip_bytes)
    excels = pick_excels(files_map)
    if not excels:
        st.error("Recebi um retorno, mas não encontrei nenhuma planilha.")
        with st.expander("Ver arquivos retornados", expanded=False):
            st.write(list(files_map.keys())[:200])
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)

    st.session_state["last_result"] = {
        "kind": "texto",
        "run_id": hdr.get("X-Run-Id", ""),
        "filename": fname,
        "excel_name": main_name,
        "excel_bytes": main_xlsx_fmt,
        "timings": {"audio_sec": 0.0, "total_sec": float(elapsed)},
    }
    st.session_state["last_run_id"] = hdr.get("X-Run-Id", "")


def run_single_audio(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()
    audio_sec = duracao_wav_seg_bytes(wav_bytes)
    if audio_sec and audio_sec > BATCH_WAV_MAX_SECONDS_EACH:
        st.error(f"Este áudio tem cerca de {audio_sec/60:.1f} minutos. Para melhor experiência, use até 10 minutos.")
        return

    update, done = make_status_ui()
    update("Preparando…", 8, None)

    try:
        update("Processando…", 22, None)
        zip_bytes, hdr, elapsed = vps_run_file(
            wav_bytes,
            wav_file.name,
            "audio/wav",
            status_cb=update,
        )
        update("Abrindo planilha…", 96, None)
    except Exception as e:
        done()
        show_friendly_error("Não foi possível concluir a avaliação.", e)
        return

    done()

    files_map = zip_extract_all(zip_bytes)
    excels = pick_excels(files_map)
    if not excels:
        st.error("Recebi um retorno, mas não encontrei nenhuma planilha.")
        with st.expander("Ver arquivos retornados", expanded=False):
            st.write(list(files_map.keys())[:200])
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)

    st.session_state["last_result"] = {
        "kind": "áudio",
        "run_id": hdr.get("X-Run-Id", ""),
        "filename": wav_file.name,
        "excel_name": main_name,
        "excel_bytes": main_xlsx_fmt,
        "timings": {"audio_sec": float(audio_sec or 0.0), "total_sec": float(elapsed)},
    }
    st.session_state["last_run_id"] = hdr.get("X-Run-Id", "")


# ==============================
# ✅ Processamento: Lote (com limites)
# ==============================
def run_batch_text(files: List[Any], pasted_blocks: List[str]):
    entradas: List[Tuple[str, str]] = []

    if files:
        for f in files:
            try:
                content = f.getvalue().decode("utf-8", errors="ignore")
            except Exception:
                content = ""
            entradas.append((f.name, content))

    if pasted_blocks:
        for i, b in enumerate(pasted_blocks, start=1):
            entradas.append((f"colado_{i}.txt", b))

    entradas = [(n, t) for (n, t) in entradas if (t or "").strip()]

    if not entradas:
        st.error("Envie arquivos ou cole pelo menos um conteúdo.")
        return

    if len(entradas) > BATCH_TEXT_MAX_ENTRIES:
        st.error(f"No modo gerencial (texto), use até {BATCH_TEXT_MAX_ENTRIES} entradas por vez (arquivos + colagens).")
        return

    for name, txt in entradas:
        ok, msg = validar_transcricao(txt)
        if not ok:
            st.error(f"{name}: {msg}")
            return

    update, done = make_status_ui()
    update("Preparando…", 8, None)

    itens: List[dict] = []
    lote_open_df = None
    lote_excel_bytes = b""
    lote_excel_name = ""

    total = len(entradas)
    for idx, (name, txt) in enumerate(entradas, start=1):
        base_progress = 14 + int(70 * (idx - 1) / max(1, total))
        update(f"Processando {idx}/{total}…", base_progress, None)

        try:
            zip_bytes, hdr, _elapsed = vps_run_file(
                txt.encode("utf-8", errors="ignore"),
                name,
                "text/plain",
                status_cb=update,
            )
        except Exception as e:
            done()
            show_friendly_error(f"Não foi possível avaliar “{name}”.", e)
            return

        files_map = zip_extract_all(zip_bytes)
        excels = pick_excels(files_map)

        indiv_name = ""
        indiv_xlsx_fmt = b""
        if excels:
            chosen = None
            for nm, xb in excels:
                if nm.lower().endswith("_spin.xlsx") or "_spin" in nm.lower():
                    chosen = (nm, xb)
                    break
            if not chosen:
                chosen = excels[0]
            indiv_name, indiv_xlsx = chosen
            indiv_xlsx_fmt = format_excel_bytes(indiv_xlsx)

        itens.append(
            {
                "idx": idx,
                "kind": "texto",
                "filename": name,
                "run_id": hdr.get("X-Run-Id", ""),
                "excel_individual_name": indiv_name,
                "excel_individual_bytes": indiv_xlsx_fmt,
            }
        )

        # Planilha do lote (se vier)
        for nm, xb in excels:
            if "spin_resultados_lote" in nm.lower():
                lote_excel_name = nm
                lote_excel_bytes = format_excel_bytes(xb)
                try:
                    lote_open_df = _safe_df(excel_bytes_to_df(lote_excel_bytes))
                except Exception:
                    lote_open_df = None
                break

    update("Finalizando…", 96, None)
    done()

    st.session_state["batch_results"] = itens
    st.session_state["batch_lote"] = {
        "excel_name": lote_excel_name,
        "excel_bytes": lote_excel_bytes,
        "df": lote_open_df,
    } if lote_excel_bytes else None
    st.session_state["last_run_id"] = (itens[-1]["run_id"] if itens else "")


def run_batch_audio(wavs: List[Any]):
    if not wavs:
        st.error("Envie pelo menos 1 áudio.")
        return

    if len(wavs) > BATCH_WAV_MAX_FILES:
        st.error(f"No modo gerencial (áudio), envie até {BATCH_WAV_MAX_FILES} arquivos por vez.")
        return

    # validar duração antes de iniciar
    for wf in wavs:
        b = wf.getbuffer().tobytes()
        d = duracao_wav_seg_bytes(b)
        if d and d > BATCH_WAV_MAX_SECONDS_EACH:
            st.error(f"“{wf.name}” tem cerca de {d/60:.1f} minutos. No lote, use até 10 minutos por áudio.")
            return

    update, done = make_status_ui()
    update("Preparando…", 8, None)

    itens: List[dict] = []
    lote_open_df = None
    lote_excel_bytes = b""
    lote_excel_name = ""

    total = len(wavs)
    for idx, wavf in enumerate(wavs, start=1):
        base_progress = 14 + int(70 * (idx - 1) / max(1, total))
        update(f"Processando {idx}/{total}…", base_progress, None)

        wav_bytes = wavf.getbuffer().tobytes()

        try:
            zip_bytes, hdr, _elapsed = vps_run_file(
                wav_bytes,
                wavf.name,
                "audio/wav",
                status_cb=update,
            )
        except Exception as e:
            done()
            show_friendly_error(f"Não foi possível avaliar “{wavf.name}”.", e)
            return

        files_map = zip_extract_all(zip_bytes)
        excels = pick_excels(files_map)

        indiv_name = ""
        indiv_xlsx_fmt = b""
        if excels:
            chosen = None
            for nm, xb in excels:
                if nm.lower().endswith("_spin.xlsx") or "_spin" in nm.lower():
                    chosen = (nm, xb)
                    break
            if not chosen:
                chosen = excels[0]
            indiv_name, indiv_xlsx = chosen
            indiv_xlsx_fmt = format_excel_bytes(indiv_xlsx)

        itens.append(
            {
                "idx": idx,
                "kind": "áudio",
                "filename": wavf.name,
                "run_id": hdr.get("X-Run-Id", ""),
                "excel_individual_name": indiv_name,
                "excel_individual_bytes": indiv_xlsx_fmt,
            }
        )

        # Planilha do lote (se vier)
        for nm, xb in excels:
            if "spin_resultados_lote" in nm.lower():
                lote_excel_name = nm
                lote_excel_bytes = format_excel_bytes(xb)
                try:
                    lote_open_df = _safe_df(excel_bytes_to_df(lote_excel_bytes))
                except Exception:
                    lote_open_df = None
                break

    update("Finalizando…", 96, None)
    done()

    st.session_state["batch_results"] = itens
    st.session_state["batch_lote"] = {
        "excel_name": lote_excel_name,
        "excel_bytes": lote_excel_bytes,
        "df": lote_open_df,
    } if lote_excel_bytes else None
    st.session_state["last_run_id"] = (itens[-1]["run_id"] if itens else "")


# ==============================
# 🧠 Cabeçalho
# ==============================
render_hero(
    title="SPIN Analyzer — Avaliação de Ligações",
    subtitle="Resultados em planilha, prontos para auditoria e acompanhamento gerencial.",
    pills=[
        "<span class='pill ok'><span class='dot'></span>Planilha (Excel)</span>",
        "<span class='pill'><span class='dot'></span>Individual e Gerencial</span>",
    ],
    icon="🎧",
)
st.markdown("---")


# ==============================
# 🧭 Sidebar (sem termos técnicos)
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")

    st.session_state["view"] = st.radio(
        "Área",
        options=["single", "batch"],
        format_func=lambda v: "👤 Avaliação Individual" if v == "single" else "📊 Visão Gerencial",
        key="view_radio",
    )

    if st.session_state["view"] != st.session_state["_prev_view"]:
        clear_all_results()
        st.session_state["_prev_view"] = st.session_state["view"]

    st.markdown("---")

    online = vps_health()
    if online:
        st.success("Serviço disponível ✅")
    else:
        st.warning("Serviço indisponível ⚠️")

    st.markdown("---")
    if st.button("🧹 Limpar resultados", use_container_width=True, key="nav_clear_all"):
        clear_all_results()


# ==============================
# ✅ UI: Telas
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")

    st.session_state["single_mode"] = st.radio(
        "Selecione o formato",
        options=["Texto", "Áudio"],
        horizontal=True,
        key="single_mode_radio",
    )
    if st.session_state["single_mode"] != st.session_state["_prev_single_mode"]:
        clear_single()
        st.session_state["_prev_single_mode"] = st.session_state["single_mode"]

    if st.session_state["single_mode"] == "Texto":
        st.markdown(
            "<div class='smallmuted mini'>O conteúdo deve marcar falas com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>",
            unsafe_allow_html=True,
        )

        txt_input = st.text_area(
            "Cole o conteúdo aqui",
            height=260,
            value="",
            key="text_input_single",
            placeholder="[VENDEDOR] ...\n[CLIENTE] ...\n[VENDEDOR] ...",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_eval_text_single"):
                clear_single()
                run_single_text(txt_input)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_text_single"):
                clear_single()

    else:
        up_wav = st.file_uploader(
            "Envie um áudio (recomendado até 10 minutos)",
            type=["wav"],
            accept_multiple_files=False,
            key="uploader_audio_single",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_eval_audio_single"):
                if up_wav is None:
                    st.error("Envie um áudio para continuar.")
                else:
                    clear_single()
                    run_single_audio(up_wav)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_audio_single"):
                clear_single()

else:
    st.markdown("### 📊 Visão Gerencial")

    st.session_state["batch_mode"] = st.radio(
        "Selecione o formato",
        options=["Texto", "Áudio"],
        horizontal=True,
        key="batch_mode_radio",
    )
    if st.session_state["batch_mode"] != st.session_state["_prev_batch_mode"]:
        clear_batch()
        st.session_state["_prev_batch_mode"] = st.session_state["batch_mode"]

    if st.session_state["batch_mode"] == "Texto":
        st.markdown(
            f"""
<div class="card">
  <div class="section-title">Limites deste modo</div>
  <div class="smallmuted">• Até <b>{BATCH_TEXT_MAX_ENTRIES}</b> entradas por vez (arquivos + colagens).</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div class='smallmuted mini'>O conteúdo deve marcar falas com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>",
            unsafe_allow_html=True,
        )

        up_texts = st.file_uploader(
            "Envie arquivos (.txt)",
            type=["txt"],
            accept_multiple_files=True,
            key="uploader_text_batch",
        )

        st.markdown("<div class='smallmuted mini'>Ou cole vários blocos separados por uma linha contendo <b>---</b></div>", unsafe_allow_html=True)
        multi_text = st.text_area(
            "Cole aqui (separe com ---)",
            height=220,
            value="",
            key="text_input_batch",
            placeholder="[VENDEDOR] ...\n[CLIENTE] ...\n---\n[VENDEDOR] ...\n[CLIENTE] ...",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_run_batch_text"):
                blocks = []
                if multi_text.strip():
                    blocks = [b.strip() for b in multi_text.split("\n---\n") if b.strip()]
                clear_batch()
                run_batch_text(up_texts or [], blocks)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_batch_text"):
                clear_batch()

    else:
        st.markdown(
            f"""
<div class="card">
  <div class="section-title">Limites deste modo</div>
  <div class="smallmuted">• Até <b>{BATCH_WAV_MAX_FILES}</b> áudios por vez.</div>
  <div class="smallmuted">• Até <b>10 minutos</b> por áudio.</div>
</div>
""",
            unsafe_allow_html=True,
        )

        up_audios = st.file_uploader(
            "Envie áudios (WAV)",
            type=["wav"],
            accept_multiple_files=True,
            key="uploader_audio_batch",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_run_batch_audio"):
                clear_batch()
                run_batch_audio(up_audios or [])

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_batch_audio"):
                clear_batch()


# ==============================
# ✅ RESULTADO: Individual
# ==============================
lr = st.session_state.get("last_result")
if lr and lr.get("excel_bytes"):
    st.markdown("---")

    kind = lr.get("kind", "")
    run_id = lr.get("run_id", "")

    pills = [f"<span class='pill ok'><span class='dot'></span>{kind.upper()}</span>"] if kind else []
    if run_id:
        pills.append(f"<span class='pill'><span class='dot'></span>Protocolo: {run_id}</span>")

    render_hero(
        title="Resultado",
        subtitle="Avaliação finalizada. Confira a planilha abaixo e faça o download quando quiser.",
        pills=pills,
        icon="✅",
    )

    try:
        df = _safe_df(excel_bytes_to_df(lr["excel_bytes"]))
    except Exception:
        df = pd.DataFrame()

    st.markdown("### 📊 Planilha (prévia)")
    if df is not None and not df.empty:
        st.dataframe(df, use_container_width=True)
        comment = summarize_excel_presence(df)
        st.markdown(
            f"""
<div class="card">
  <div class="section-title">📌 Observação</div>
  <p style="margin-top:10px;margin-bottom:0;">{comment}</p>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        st.warning("Não consegui abrir a prévia da planilha aqui, mas o download está disponível.")

    timings = lr.get("timings", {}) or {}
    audio_sec = float(timings.get("audio_sec", 0) or 0)
    total_sec = float(timings.get("total_sec", 0) or 0)
    render_time_card(audio_sec, total_sec)

    render_downloads_explain()

    filename = lr.get("filename") or f"avaliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base = Path(filename).stem

    st.download_button(
        "📥 Baixar planilha (Excel)",
        data=lr.get("excel_bytes", b""),
        file_name=f"{base}_avaliacao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"dl_excel_single_{base}",
    )


# ==============================
# ✅ RESULTADO: Lote
# ==============================
br = st.session_state.get("batch_results")
batch_lote = st.session_state.get("batch_lote")

if br:
    st.markdown("---")
    render_hero(
        title="Resultados do lote",
        subtitle="Planilha consolidada + planilhas individuais por arquivo.",
        pills=[
            "<span class='pill ok'><span class='dot'></span>Consolidado</span>",
            "<span class='pill'><span class='dot'></span>Individuais</span>",
        ],
        icon="📊",
    )

    if batch_lote and batch_lote.get("excel_bytes"):
        st.markdown("### 📊 Planilha do lote (prévia)")
        df_lote = batch_lote.get("df")
        if isinstance(df_lote, pd.DataFrame) and not df_lote.empty:
            st.dataframe(df_lote, use_container_width=True)
        else:
            st.warning("Não consegui abrir a prévia do lote aqui, mas o download está disponível.")

    render_downloads_explain()

    if batch_lote and batch_lote.get("excel_bytes"):
        st.download_button(
            "📥 Baixar planilha do lote (Excel)",
            data=batch_lote["excel_bytes"],
            file_name=f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_excel_lote",
        )

    st.markdown("### 📁 Planilhas individuais")
    for item in br:
        idx = item.get("idx", 0)
        filename = str(item.get("filename") or f"item_{idx}")
        base = Path(filename).stem

        with st.expander(f"📌 {idx}. {filename}", expanded=False):
            xb = item.get("excel_individual_bytes", b"")
            if xb:
                st.download_button(
                    "📥 Baixar planilha (Excel)",
                    data=xb,
                    file_name=f"{base}_avaliacao.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_excel_item_{idx}_{base}",
                )
            else:
                st.warning("Planilha individual não disponível para este item.")


# ==============================
# 🧾 Rodapé
# ==============================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3A4A63;'>"
    "SPIN Analyzer — Projeto Tele_IA 2026 | Desenvolvido por Paulo Coutinho"
    "</div>",
    unsafe_allow_html=True,
)
