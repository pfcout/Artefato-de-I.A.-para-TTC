# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT + WAV)
# MODO ÚNICO: VPS (Streamlit / Cloud)
# ✅ Endpoint único: POST {VPS_BASE_URL}/run  (05_api_vps.py)
# ✅ Individual: retorna apenas Excel principal (sem ZIP / sem logs)
# ✅ Gerencial (lote): Excel do lote aberto + downloads (Excel lote + Excel por item)
# ✅ Limpa resultado ao trocar de aba/tela + botão “Limpar”
# ✅ Barra de progresso + tempo decorrido (estimativa só quando der)
# ✅ Excel formatado (wrap + largura + freeze)
# ✅ Corrige: UI “travada” sem progresso (thread), tabs bug (radio), health 503 no meio (cache + pausa)
# ===============================================

import os
import re
import io
import time
import zipfile
import wave
import threading
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

if MODE != "VPS":
    st.error("❌ Este painel funciona apenas em VPS. Ajuste MODE='VPS' nos secrets.")
    st.stop()
if not VPS_BASE_URL:
    st.error("❌ VPS_BASE_URL não configurado (Secrets/Env).")
    st.stop()
if not VPS_API_KEY:
    st.error("❌ VPS_API_KEY não configurado (Secrets/Env).")
    st.stop()


def _pretty_url(u: str) -> str:
    return (u or "").strip()


# ==============================
# 🎨 Estilo profissional
# ==============================
st.markdown(
    """
<style>
body { background-color:#FFFFFF; color:#0B1220; font-family:Segoe UI, Arial, sans-serif; }
h1,h2,h3 { color:#0B63F3; }

.card{
  background:#FFFFFF !important;
  color:#0B1220 !important;
  border:1px solid #C7D6F5 !important;
  border-radius:18px;
  padding:16px 18px;
  margin-bottom:12px;
  box-shadow:0 8px 24px rgba(11,18,32,0.08);
}
.card *{ color:#0B1220 !important; }

.badge{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  border:1px solid #AFC7F3 !important;
  background:#F6F9FF !important;
  color:#0B63F3 !important;
  font-weight:800;
  font-size:0.9rem;
}
.badge.ok{
  background:#E6FFF3 !important;
  border-color:#29B37C !important;
  color:#0B6B4B !important;
}
.smallmuted{ color:#3A4A63; font-weight:600; }
hr { margin: 1.25rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

# ==============================
# 🧠 Estado do app
# ==============================
def _ensure_state():
    ss = st.session_state
    ss.setdefault("view", "single")                # single | batch
    ss.setdefault("single_mode", "txt")            # txt | wav
    ss.setdefault("batch_mode", "txt")             # txt | wav

    ss.setdefault("last_result", None)             # dict
    ss.setdefault("batch_results", None)           # list[dict]
    ss.setdefault("batch_lote", None)              # dict

    ss.setdefault("processing", False)
    ss.setdefault("last_run_id", "")

    # histórico simples p/ estimativa (EMA)
    ss.setdefault("ema_txt_sec", None)
    ss.setdefault("ema_wav_sec", None)
    ss.setdefault("ema_batch_item_sec", None)


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
# ✅ Validação do TXT
# ==============================
def validar_transcricao(txt: str) -> Tuple[bool, str]:
    linhas = [l.strip() for l in (txt or "").splitlines() if l.strip()]
    if len(linhas) < 4:
        return False, "Texto muito curto."
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
    sec = max(0.0, sec)
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
# 🌐 VPS Health (cache + pausa durante processamento)
# ==============================
@st.cache_data(ttl=5)
def _vps_health_cached(url: str) -> Tuple[bool, Dict[str, Any]]:
    try:
        r = requests.get(f"{url}/health", timeout=(3, 6))
        if r.status_code != 200:
            return False, {}
        try:
            return True, r.json()
        except Exception:
            return True, {}
    except Exception:
        return False, {}


def vps_health_ui() -> Tuple[bool, Dict[str, Any]]:
    if st.session_state.get("processing"):
        # não “derruba” o usuário com indisponível enquanto processa
        return True, {}
    return _vps_health_cached(VPS_BASE_URL)


# ==============================
# 🌐 API — VPS
# ==============================
def vps_run_file(file_bytes: bytes, filename: str, mime: str) -> Tuple[bytes, Dict[str, str]]:
    files = {"file": (filename, file_bytes, mime)}
    headers = {"X-API-KEY": VPS_API_KEY}
    r = requests.post(
        f"{VPS_BASE_URL}/run",
        files=files,
        headers=headers,
        timeout=REQ_TIMEOUT,
    )
    r.raise_for_status()
    useful = {
        "X-Run-Id": r.headers.get("X-Run-Id", ""),
        "X-Debug": r.headers.get("X-Debug", ""),
    }
    return r.content, useful


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


def pick_txts(files_map: Dict[str, bytes]) -> List[Tuple[str, bytes]]:
    # geralmente: .../txt/arquivo.txt
    out = []
    for k, v in files_map.items():
        kl = k.lower()
        if kl.endswith(".txt") and "/txt/" in kl:
            out.append((k, v))
    return out


def summarize_excel_presence(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "Não foi possível abrir a planilha gerada."

    cols = [str(c).strip() for c in df.columns]
    phase_cols = [c for c in cols if c.lower().startswith("check_") or re.match(r"^p[0-4]", c.lower())]
    if not phase_cols:
        return "Planilha gerada com sucesso. Revise as colunas do relatório para interpretar os resultados."

    try:
        dfn = df[phase_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        total = float(dfn.sum().sum())
        if total == 0.0:
            return "As colunas de fases existem, mas o resultado ficou zerado neste arquivo. Isso pode ocorrer em conversas curtas ou sem evidências claras das etapas."
        return "As fases do método aparecem na planilha. Use as colunas de fases e (se houver) trechos/justificativas para validar a identificação."
    except Exception:
        return "As colunas de fases aparecem na planilha, mas os valores não puderam ser interpretados automaticamente. Revise manualmente as colunas de fases e justificativas."


# ==============================
# 🧩 UI helpers
# ==============================
def render_badges_public(kind: str = "", run_id: str = ""):
    parts = []
    if kind:
        parts.append(f'<span class="badge ok">{kind.upper()}</span>')
    if run_id:
        parts.append(f'<span class="badge">Protocolo: {run_id}</span>')

    st.markdown(
        f"""<div class="card"><p style="margin:0;">{"&nbsp;&nbsp;".join(parts) if parts else "—"}</p></div>""",
        unsafe_allow_html=True,
    )


def render_time_card(audio_sec: float, total_sec: float):
    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">⏱️ Tempo</h3>
  <p style="margin-top:10px;margin-bottom:0;">
    <span class="badge">Ligação</span> <b>{human_time(audio_sec)}</b>
    &nbsp;&nbsp;&nbsp;
    <span class="badge">Processamento</span> <b>{human_time(total_sec)}</b>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


def downloads_explain_individual():
    st.markdown(
        """
<div class="card">
  <h3 style="margin:0;">📥 Downloads</h3>
  <p class="smallmuted" style="margin:8px 0 0 0;">
    Baixe a planilha de avaliação pronta para abrir no Excel.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


def downloads_explain_batch():
    st.markdown(
        """
<div class="card">
  <h3 style="margin:0;">📥 Downloads</h3>
  <p class="smallmuted" style="margin:8px 0 0 0;">
    <b>Excel do lote</b> consolida todos os arquivos. <br/>
    <b>Excel individual</b> é uma planilha separada por arquivo. <br/>
    Em envios por áudio, a <b>transcrição (TXT)</b> também fica disponível.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


# ==============================
# ⏳ Progresso + timer (FUNCIONA durante o POST)
# ==============================
def run_with_progress(
    title: str,
    phases: List[Tuple[str, float]],
    target_func,
    estimate_total_sec: Optional[float] = None,
):
    """
    Executa target_func em thread e atualiza UI (timer + progress) em loop.
    phases: lista de (nome, peso acumulado 0..1) para mensagens “trocarem”.
    estimate_total_sec: só usado se já tivermos histórico (EMA).
    """
    st.session_state["processing"] = True

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

    # loop de UI
    phase_idx = 0
    last_msg = ""
    while th.is_alive():
        elapsed = time.time() - t0

        # progresso heurístico: sobe com o tempo, sem “prometer” 100%
        if estimate_total_sec and estimate_total_sec > 2:
            p = min(0.92, elapsed / max(estimate_total_sec, 1.0))
        else:
            # sem histórico: cresce devagar e trava em 0.85
            p = min(0.85, elapsed / 120.0)  # 2min = 100% heurístico (capado)
        pbar.progress(max(0.01, float(p)))

        # fase/mensagem
        if estimate_total_sec and estimate_total_sec > 2:
            frac = min(0.999, elapsed / estimate_total_sec)
        else:
            frac = min(0.999, p / 0.92)

        # escolhe fase pelo frac
        for i, (_, w) in enumerate(phases):
            if frac <= w:
                phase_idx = i
                break
        msg = phases[phase_idx][0] if phases else title

        if msg != last_msg:
            status_line.markdown(
                f"<div class='smallmuted'>• {msg}</div>",
                unsafe_allow_html=True,
            )
            last_msg = msg

        if estimate_total_sec and estimate_total_sec > elapsed:
            timer_line.markdown(
                f"<div class='smallmuted'>⏳ Rodando há <b>{human_time(elapsed)}</b> • estimativa: <b>{human_time(estimate_total_sec)}</b></div>",
                unsafe_allow_html=True,
            )
        else:
            timer_line.markdown(
                f"<div class='smallmuted'>⏳ Rodando há <b>{human_time(elapsed)}</b></div>",
                unsafe_allow_html=True,
            )

        time.sleep(0.15)

    # thread terminou
    elapsed = time.time() - t0
    pbar.progress(1.0)
    time.sleep(0.05)
    status_line.empty()
    timer_line.empty()
    pbar.empty()
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
# ✅ Processamento: Individual
# ==============================
def run_single_txt(txt: str):
    ok, msg = validar_transcricao(txt)
    if not ok:
        st.error(msg)
        return

    fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    est = st.session_state.get("ema_txt_sec")

    phases = [
        ("Preparando avaliação…", 0.10),
        ("Enviando conteúdo…", 0.25),
        ("Avaliando conversa…", 0.80),
        ("Gerando planilha…", 0.95),
        ("Finalizando…", 1.00),
    ]

    def _do():
        zip_bytes, hdr = vps_run_file(txt.encode("utf-8", errors="ignore"), fname, "text/plain")
        return zip_bytes, hdr

    try:
        (zip_bytes, hdr), elapsed = run_with_progress(
            "Avaliando…",
            phases=phases,
            target_func=_do,
            estimate_total_sec=est,
        )
    except requests.exceptions.ConnectTimeout:
        st.error("❌ Não consegui conectar ao servidor.")
        st.caption(f"Servidor: {_pretty_url(VPS_BASE_URL)}")
        return
    except requests.exceptions.ReadTimeout:
        st.error("❌ O servidor demorou para responder (timeout).")
        st.caption("Tente um arquivo menor ou aumente API_TIMEOUT_S.")
        return
    except requests.exceptions.HTTPError as e:
        st.error("❌ O servidor retornou erro.")
        st.code(str(e))
        return
    except Exception as e:
        st.error("❌ Não foi possível concluir a avaliação.")
        st.code(str(e))
        return

    _ema_update("ema_txt_sec", elapsed)

    files_map = zip_extract_all(zip_bytes)
    excels = pick_excels(files_map)
    if not excels:
        st.error("❌ O servidor retornou um resultado, mas não encontrei nenhum Excel.")
        st.write(list(files_map.keys())[:200])
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)
    df = _safe_df(excel_bytes_to_df(main_xlsx_fmt))

    st.session_state["last_result"] = {
        "kind": "txt",
        "run_id": hdr.get("X-Run-Id", ""),
        "filename": fname,
        "excel_name": main_name,
        "excel_bytes": main_xlsx_fmt,
        "df": df,
        "timings": {"audio_sec": 0.0, "total_sec": float(elapsed)},
    }
    st.session_state["last_run_id"] = hdr.get("X-Run-Id", "")


def run_single_wav(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()
    audio_sec = duracao_wav_seg_bytes(wav_bytes)
    if audio_sec and audio_sec > 600:
        st.error(f"❌ Áudio tem {audio_sec/60:.1f} minutos. Limite recomendado: 10 minutos.")
        return

    est = st.session_state.get("ema_wav_sec")

    phases = [
        ("Preparando avaliação…", 0.10),
        ("Enviando áudio…", 0.25),
        ("Transcrevendo áudio…", 0.55),
        ("Avaliando conversa…", 0.85),
        ("Gerando planilha…", 0.95),
        ("Finalizando…", 1.00),
    ]

    def _do():
        zip_bytes, hdr = vps_run_file(wav_bytes, wav_file.name, "audio/wav")
        return zip_bytes, hdr

    try:
        (zip_bytes, hdr), elapsed = run_with_progress(
            "Avaliando…",
            phases=phases,
            target_func=_do,
            estimate_total_sec=est,
        )
    except requests.exceptions.ConnectTimeout:
        st.error("❌ Não consegui conectar ao servidor.")
        st.caption(f"Servidor: {_pretty_url(VPS_BASE_URL)}")
        return
    except requests.exceptions.ReadTimeout:
        st.error("❌ O servidor demorou para responder (timeout).")
        st.caption("Tente um áudio menor ou aumente API_TIMEOUT_S.")
        return
    except requests.exceptions.HTTPError as e:
        st.error("❌ O servidor retornou erro.")
        st.code(str(e))
        return
    except Exception as e:
        st.error("❌ Não foi possível concluir a avaliação.")
        st.code(str(e))
        return

    _ema_update("ema_wav_sec", elapsed)

    files_map = zip_extract_all(zip_bytes)
    excels = pick_excels(files_map)
    if not excels:
        st.error("❌ O servidor retornou um resultado, mas não encontrei nenhum Excel.")
        st.write(list(files_map.keys())[:200])
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)
    df = _safe_df(excel_bytes_to_df(main_xlsx_fmt))

    txts = pick_txts(files_map)
    txt_best = txts[0][1].decode("utf-8", errors="ignore") if txts else ""

    st.session_state["last_result"] = {
        "kind": "wav",
        "run_id": hdr.get("X-Run-Id", ""),
        "filename": wav_file.name,
        "excel_name": main_name,
        "excel_bytes": main_xlsx_fmt,
        "df": df,
        "timings": {"audio_sec": float(audio_sec or 0.0), "total_sec": float(elapsed)},
        "txt_rotulado": txt_best,
    }
    st.session_state["last_run_id"] = hdr.get("X-Run-Id", "")


# ==============================
# ✅ Processamento: Lote (até 10)
# ==============================
def run_batch_txt(files: List[Any], pasted_blocks: List[str]):
    entradas: List[Tuple[str, str]] = []
    if files:
        for f in files[:10]:
            entradas.append((f.name, f.getvalue().decode("utf-8", errors="ignore")))
    if pasted_blocks:
        for i, b in enumerate(pasted_blocks[:10], start=1):
            entradas.append((f"colado_{i}.txt", b))

    if not entradas:
        st.error("Envie TXT(s) ou cole pelo menos um bloco.")
        return

    for name, txt in entradas:
        ok, msg = validar_transcricao(txt)
        if not ok:
            st.error(f"❌ {name}: {msg}")
            return

    est_item = st.session_state.get("ema_batch_item_sec")
    est_total = (est_item * len(entradas)) if est_item else None

    phases = [
        ("Preparando lote…", 0.10),
        ("Enviando arquivos…", 0.25),
        ("Avaliando lote…", 0.85),
        ("Consolidando planilha…", 0.95),
        ("Finalizando…", 1.00),
    ]

    def _do():
        itens: List[dict] = []
        lote_excel_payload = None
        for idx, (name, txt) in enumerate(entradas, start=1):
            zip_bytes, hdr = vps_run_file(txt.encode("utf-8", errors="ignore"), name, "text/plain")
            files_map = zip_extract_all(zip_bytes)
            excels = pick_excels(files_map)

            # individual do item: preferir _SPIN.xlsx
            indiv_name = ""
            indiv_xlsx_fmt = b""
            chosen = None
            for nm, xb in excels:
                if nm.lower().endswith("_spin.xlsx") or "_spin" in nm.lower():
                    chosen = (nm, xb)
                    break
            if not chosen and excels:
                chosen = excels[0]
            if chosen:
                indiv_name, indiv_xlsx = chosen
                indiv_xlsx_fmt = format_excel_bytes(indiv_xlsx)

            itens.append(
                {
                    "idx": idx,
                    "kind": "txt",
                    "filename": name,
                    "run_id": hdr.get("X-Run-Id", ""),
                    "excel_individual_name": indiv_name,
                    "excel_individual_bytes": indiv_xlsx_fmt,
                }
            )

            # lote (consolidado): SPIN_RESULTADOS_LOTE
            for nm, xb in excels:
                if "spin_resultados_lote" in nm.lower():
                    lote_excel_payload = (nm, format_excel_bytes(xb))
                    break

        return itens, lote_excel_payload

    try:
        (itens, lote_excel_payload), elapsed = run_with_progress(
            "Processando lote…",
            phases=phases,
            target_func=_do,
            estimate_total_sec=est_total,
        )
    except Exception as e:
        st.error("❌ Não foi possível concluir o lote.")
        st.code(str(e))
        return

    # atualiza EMA por item
    if len(entradas) > 0:
        _ema_update("ema_batch_item_sec", elapsed / max(1, len(entradas)))

    st.session_state["batch_results"] = itens
    st.session_state["last_run_id"] = (itens[-1]["run_id"] if itens else "")

    if lote_excel_payload:
        nm, xb = lote_excel_payload
        st.session_state["batch_lote"] = {
            "excel_name": nm,
            "excel_bytes": xb,
            "df": _safe_df(excel_bytes_to_df(xb)),
        }
    else:
        st.session_state["batch_lote"] = None


def run_batch_wav(wavs: List[Any]):
    if not wavs:
        st.error("Envie pelo menos 1 WAV.")
        return
    wavs = wavs[:10]

    est_item = st.session_state.get("ema_batch_item_sec")
    est_total = (est_item * len(wavs)) if est_item else None

    phases = [
        ("Preparando lote…", 0.10),
        ("Enviando áudios…", 0.25),
        ("Transcrevendo e avaliando…", 0.85),
        ("Consolidando planilha…", 0.95),
        ("Finalizando…", 1.00),
    ]

    def _do():
        itens: List[dict] = []
        lote_excel_payload = None
        for idx, wavf in enumerate(wavs, start=1):
            wav_bytes = wavf.getbuffer().tobytes()
            zip_bytes, hdr = vps_run_file(wav_bytes, wavf.name, "audio/wav")
            files_map = zip_extract_all(zip_bytes)
            excels = pick_excels(files_map)

            chosen = None
            for nm, xb in excels:
                if nm.lower().endswith("_spin.xlsx") or "_spin" in nm.lower():
                    chosen = (nm, xb)
                    break
            if not chosen and excels:
                chosen = excels[0]

            indiv_name = ""
            indiv_xlsx_fmt = b""
            if chosen:
                indiv_name, indiv_xlsx = chosen
                indiv_xlsx_fmt = format_excel_bytes(indiv_xlsx)

            txts = pick_txts(files_map)
            txt_best = txts[0][1].decode("utf-8", errors="ignore") if txts else ""

            itens.append(
                {
                    "idx": idx,
                    "kind": "wav",
                    "filename": wavf.name,
                    "run_id": hdr.get("X-Run-Id", ""),
                    "excel_individual_name": indiv_name,
                    "excel_individual_bytes": indiv_xlsx_fmt,
                    "txt_rotulado": txt_best,
                }
            )

            for nm, xb in excels:
                if "spin_resultados_lote" in nm.lower():
                    lote_excel_payload = (nm, format_excel_bytes(xb))
                    break

        return itens, lote_excel_payload

    try:
        (itens, lote_excel_payload), elapsed = run_with_progress(
            "Processando lote…",
            phases=phases,
            target_func=_do,
            estimate_total_sec=est_total,
        )
    except Exception as e:
        st.error("❌ Não foi possível concluir o lote.")
        st.code(str(e))
        return

    if len(wavs) > 0:
        _ema_update("ema_batch_item_sec", elapsed / max(1, len(wavs)))

    st.session_state["batch_results"] = itens
    st.session_state["last_run_id"] = (itens[-1]["run_id"] if itens else "")

    if lote_excel_payload:
        nm, xb = lote_excel_payload
        st.session_state["batch_lote"] = {
            "excel_name": nm,
            "excel_bytes": xb,
            "df": _safe_df(excel_bytes_to_df(xb)),
        }
    else:
        st.session_state["batch_lote"] = None


# ==============================
# 🧠 Cabeçalho
# ==============================
st.markdown("## 🎧 SPIN Analyzer — Avaliação de Ligações")
st.markdown(
    "Análise automática de ligações de **Televendas Técnico-Consultivas (TTC)** "
    "com base no método **SPIN Selling**."
)
st.markdown("---")


# ==============================
# 🧭 Sidebar (sem técnica)
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")

    if st.button("👤 Avaliação Individual", use_container_width=True, key="nav_single"):
        if st.session_state["view"] != "single":
            clear_all_results()
        st.session_state["view"] = "single"
        st.rerun()

    if st.button("📊 Visão Gerencial", use_container_width=True, key="nav_batch"):
        if st.session_state["view"] != "batch":
            clear_all_results()
        st.session_state["view"] = "batch"
        st.rerun()

    st.markdown("---")

    online, health_json = vps_health_ui()
    if online:
        st.success("Servidor conectado ✅")
    else:
        st.warning("Servidor indisponível ⚠️")

    st.markdown("---")
    if st.button("🧹 Limpar", use_container_width=True, key="nav_clear_all"):
        clear_all_results()
        st.rerun()


# ==============================
# ✅ UI: Telas (SEM tabs bugadas)
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")

    single_mode = st.radio(
        "Entrada",
        options=["txt", "wav"],
        format_func=lambda x: "📝 Texto" if x == "txt" else "🎧 Áudio",
        horizontal=True,
        key="radio_single_mode",
    )

    # reset ao trocar
    if single_mode != st.session_state.get("single_mode"):
        clear_single()
        st.session_state["single_mode"] = single_mode

    if single_mode == "txt":
        st.markdown(
            "<div class='smallmuted'>O texto deve começar as falas com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>",
            unsafe_allow_html=True,
        )
        txt_input = st.text_area(
            "Cole a transcrição aqui",
            height=260,
            value="",
            key="txt_input_single",
            placeholder="[VENDEDOR] ...\n[CLIENTE] ...\n[VENDEDOR] ...",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_eval_txt_single"):
                clear_single()
                run_single_txt(txt_input)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_txt_single"):
                clear_single()
                st.rerun()

    else:
        up_wav = st.file_uploader(
            "Envie um WAV (até ~10 min)",
            type=["wav"],
            accept_multiple_files=False,
            key="uploader_wav_single",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_eval_wav_single"):
                if up_wav is None:
                    st.error("Envie um WAV para continuar.")
                else:
                    clear_single()
                    run_single_wav(up_wav)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_wav_single"):
                clear_single()
                st.rerun()

else:
    st.markdown("### 📊 Visão Gerencial (até 10)")

    batch_mode = st.radio(
        "Entrada",
        options=["txt", "wav"],
        format_func=lambda x: "📝 Texto" if x == "txt" else "🎧 Áudio",
        horizontal=True,
        key="radio_batch_mode",
    )

    if batch_mode != st.session_state.get("batch_mode"):
        clear_batch()
        st.session_state["batch_mode"] = batch_mode

    if batch_mode == "txt":
        st.markdown(
            "<div class='smallmuted'>Os textos devem começar as falas com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>",
            unsafe_allow_html=True,
        )
        up_txts = st.file_uploader(
            "Envie até 10 arquivos .txt",
            type=["txt"],
            accept_multiple_files=True,
            key="uploader_txt_batch",
        )

        st.markdown("Ou cole vários blocos separados por uma linha contendo `---`")
        multi_txt = st.text_area(
            "Cole aqui (separe com ---)",
            height=220,
            value="",
            key="txt_input_batch",
            placeholder="[VENDEDOR] ...\n[CLIENTE] ...\n---\n[VENDEDOR] ...\n[CLIENTE] ...",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_run_batch_txt"):
                blocks = []
                if multi_txt.strip():
                    blocks = [b.strip() for b in multi_txt.split("\n---\n") if b.strip()]
                clear_batch()
                run_batch_txt(up_txts or [], blocks)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_batch_txt"):
                clear_batch()
                st.rerun()

    else:
        up_wavs = st.file_uploader(
            "Envie até 10 WAVs",
            type=["wav"],
            accept_multiple_files=True,
            key="uploader_wav_batch",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Iniciar avaliação", use_container_width=True, key="btn_run_batch_wav"):
                clear_batch()
                run_batch_wav(up_wavs or [])

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_batch_wav"):
                clear_batch()
                st.rerun()


# ==============================
# ✅ RESULTADO: Individual
# Excel primeiro, tempo abaixo, observação curta, downloads sem ZIP
# ==============================
lr = st.session_state.get("last_result")
if lr and isinstance(lr.get("df"), pd.DataFrame):
    st.markdown("---")
    st.markdown("## ✅ Resultado")

    render_badges_public(kind=lr.get("kind", ""), run_id=lr.get("run_id", ""))

    df = lr["df"]
    st.markdown("### 📊 Planilha (aberta)")
    st.dataframe(df, use_container_width=True)

    timings = lr.get("timings", {}) or {}
    audio_sec = float(timings.get("audio_sec", 0) or 0)
    total_sec = float(timings.get("total_sec", 0) or 0)
    render_time_card(audio_sec, total_sec)

    comment = summarize_excel_presence(df)
    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">📌 Observação</h3>
  <p style="margin-top:10px;margin-bottom:0;">{comment}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    downloads_explain_individual()

    filename = lr.get("filename") or f"avaliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base = Path(filename).stem

    st.download_button(
        "📥 Baixar Excel",
        data=lr.get("excel_bytes", b""),
        file_name=f"{base}_avaliacao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"dl_excel_single_{base}",
    )

    if lr.get("kind") == "wav":
        txt_rot = (lr.get("txt_rotulado") or "").strip()
        if txt_rot:
            st.download_button(
                "📥 Baixar transcrição (TXT)",
                data=txt_rot,
                file_name=f"{base}_transcricao.txt",
                use_container_width=True,
                key=f"dl_txt_single_{base}",
            )


# ==============================
# ✅ RESULTADO: Lote
# Excel do lote ABERTO (prioritário) + downloads
# ==============================
br = st.session_state.get("batch_results")
batch_lote = st.session_state.get("batch_lote")

if br:
    st.markdown("---")
    st.markdown("## ✅ Resultados do lote")

    if batch_lote and isinstance(batch_lote.get("df"), pd.DataFrame) and not batch_lote["df"].empty:
        st.markdown("### 📊 Planilha do lote (aberta)")
        st.dataframe(batch_lote["df"], use_container_width=True)

    downloads_explain_batch()

    if batch_lote and batch_lote.get("excel_bytes"):
        st.download_button(
            "📥 Baixar Excel do lote",
            data=batch_lote["excel_bytes"],
            file_name=f"lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_excel_lote",
        )

    st.markdown("### 📁 Arquivos individuais")
    for item in br:
        idx = item.get("idx", 0)
        filename = str(item.get("filename") or f"item_{idx}")
        base = Path(filename).stem

        with st.expander(f"📌 {idx}. {filename}", expanded=False):
            xb = item.get("excel_individual_bytes", b"")
            if xb:
                st.download_button(
                    "📥 Baixar Excel (individual)",
                    data=xb,
                    file_name=f"{base}_avaliacao.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_excel_item_{idx}_{base}",
                )
            else:
                st.warning("Excel individual não disponível para este item.")

            if item.get("kind") == "wav":
                txt_rot = (item.get("txt_rotulado") or "").strip()
                if txt_rot:
                    st.download_button(
                        "📥 Baixar transcrição (TXT)",
                        data=txt_rot,
                        file_name=f"{base}_transcricao.txt",
                        use_container_width=True,
                        key=f"dl_txt_item_{idx}_{base}",
                    )


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
