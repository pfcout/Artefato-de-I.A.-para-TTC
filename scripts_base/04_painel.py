# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT + WAV)
# MODO ÚNICO: VPS (Streamlit / Cloud)
# ✅ Endpoint único: POST {VPS_BASE_URL}/run  (05_api_vps.py)
# ✅ Individual: retorna apenas Excel principal (sem ZIP / sem logs)
# ✅ Gerencial (lote): Excel do lote aberto + downloads (Excel lote + Excel por item)
# ✅ Limpa resultado ao trocar de aba/tela + botão “Limpar”
# ✅ Barra de progresso + tempo decorrido (estimativa só quando der)
# ✅ Excel formatado (wrap + largura + freeze)
# ✅ Ajuste visual: header “Resultado” + “Protocolo/Tipo” mais elegante (sem cards brancos gigantes)
# ===============================================

import os
import re
import io
import time
import json
import zipfile
import shutil
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
# 🎨 Estilo profissional (mantido + melhorias nas áreas solicitadas)
# ==============================
st.markdown(
    """
<style>
/* Base */
body {
  background-color: #FFFFFF;
  color: #0B1220;
  font-family: Segoe UI, Arial, sans-serif;
}
h1, h2, h3 { color: #0B63F3; }

/* Cards padrão */
.card{
  background: #FFFFFF !important;
  color: #0B1220 !important;
  border: 1px solid #C7D6F5 !important;
  border-radius: 18px;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: 0 8px 24px rgba(11,18,32,0.08);
}
.card *{ color: #0B1220 !important; }
.smallmuted{ color:#3A4A63; font-weight:600; }

/* Pills / badges */
.pill-row{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  align-items:center;
}
.pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:8px 12px;
  border-radius:999px;
  border: 1px solid #AFC7F3;
  background: #F6F9FF;
  color:#0B63F3;
  font-weight:800;
  font-size:0.92rem;
  line-height:1;
}
.pill .dot{
  width:9px; height:9px; border-radius:999px;
  background:#0B63F3;
  display:inline-block;
}
.pill.ok{
  background:#E6FFF3;
  border-color:#29B37C;
  color:#0B6B4B;
}
.pill.ok .dot{ background:#29B37C; }
.pill.neutral{
  background:#F6F9FF;
  border-color:#AFC7F3;
  color:#0B63F3;
}

/* Header “Resultado” (substitui aquele fundo branco grande) */
.result-hero{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:14px;
  padding:18px;
  border-radius:22px;
  border: 1px solid rgba(199,214,245,0.85);
  background: linear-gradient(135deg, rgba(246,249,255,1) 0%, rgba(255,255,255,1) 55%, rgba(230,255,243,0.65) 100%);
  box-shadow: 0 12px 30px rgba(11,18,32,0.10);
  margin-top: 8px;
  margin-bottom: 14px;
}
.result-hero .left{
  display:flex;
  gap:12px;
  align-items:flex-start;
}
.result-hero .icon{
  width:42px;
  height:42px;
  border-radius:14px;
  background:#E6FFF3;
  border:1px solid #29B37C;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:22px;
}
.result-hero .title{
  margin:0;
  font-size:1.45rem;
  font-weight:900;
  color:#0B1220;
}
.result-hero .subtitle{
  margin:6px 0 0 0;
  color:#3A4A63;
  font-weight:650;
}

/* Status card (durante execução) mais “clean” */
.status-card{
  background: linear-gradient(135deg, #FFFFFF 0%, #F6F9FF 55%, #FFFFFF 100%) !important;
  border: 1px solid #C7D6F5 !important;
  border-radius: 18px !important;
  padding: 16px 18px !important;
  box-shadow: 0 10px 26px rgba(11,18,32,0.08);
}
.status-title{
  margin:0 !important;
  font-size:1.10rem !important;
  font-weight:900 !important;
  color:#0B1220 !important;
}
.status-sub{
  margin:6px 0 0 0 !important;
  color:#3A4A63 !important;
  font-weight:650 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==============================
# 🧠 Estado do app
# ==============================
def _ensure_state():
    if "view" not in st.session_state:
        st.session_state["view"] = "single"  # single | batch
    if "single_tab" not in st.session_state:
        st.session_state["single_tab"] = "txt"  # txt | wav
    if "batch_tab" not in st.session_state:
        st.session_state["batch_tab"] = "txt"  # txt | wav

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "batch_results" not in st.session_state:
        st.session_state["batch_results"] = None
    if "batch_lote" not in st.session_state:
        st.session_state["batch_lote"] = None  # dict com excel do lote aberto

    if "last_run_id" not in st.session_state:
        st.session_state["last_run_id"] = ""


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
# 🌐 API — VPS (05_api_vps.py)
# ==============================
def vps_health() -> bool:
    try:
        r = requests.get(f"{VPS_BASE_URL}/health", timeout=(3, 6))
        return r.status_code == 200
    except Exception:
        return False


def vps_run_file(file_bytes: bytes, filename: str, mime: str, status_cb=None) -> Tuple[bytes, Dict[str, str], float]:
    files = {"file": (filename, file_bytes, mime)}
    headers = {"X-API-KEY": VPS_API_KEY}

    t0 = time.time()
    try:
        if status_cb:
            status_cb("Preparando envio…", 0.10, None)

        r = requests.post(
            f"{VPS_BASE_URL}/run",
            files=files,
            headers=headers,
            timeout=REQ_TIMEOUT,
        )

        if status_cb:
            status_cb("Finalizando…", 0.95, None)

        r.raise_for_status()
        zip_bytes = r.content
        useful = {
            "X-Run-Id": r.headers.get("X-Run-Id", ""),
            "X-Debug": r.headers.get("X-Debug", ""),
        }
        return zip_bytes, useful, (time.time() - t0)

    except requests.exceptions.ConnectTimeout:
        raise RuntimeError(
            "Não consegui CONECTAR na VPS.\n"
            "Possíveis causas: porta fechada, URL incorreta, servidor fora do ar.\n"
            f"Servidor: {_pretty_url(VPS_BASE_URL)}\n"
            f"Timeout(connect/read): {CONNECT_TIMEOUT_S}s / {READ_TIMEOUT_S}s"
        )
    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            "Conectei na VPS, mas ela demorou para responder.\n"
            "Tente um áudio menor ou aumente API_TIMEOUT_S."
        )
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "Falha de rede ao acessar a VPS.\n"
            f"Servidor: {_pretty_url(VPS_BASE_URL)}\nDetalhe: {e}"
        )
    except requests.exceptions.HTTPError:
        try:
            body = r.text[:800]
            code = r.status_code
        except Exception:
            body = "—"
            code = "—"
        raise RuntimeError(f"Servidor respondeu com erro.\nStatus: {code}\nBody: {body}")
    except Exception as e:
        raise RuntimeError(f"Erro inesperado ao chamar a VPS: {e}")


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
    return [(k, v) for k, v in files_map.items() if k.lower().endswith(".txt") and "/txt/" in k.lower()]


def summarize_excel_presence(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "Não foi possível abrir a planilha gerada."

    cols = [str(c).strip() for c in df.columns]
    phase_cols = [c for c in cols if c.lower().startswith("check_") or re.match(r"^p[0-4]", c.lower())]
    if not phase_cols:
        return (
            "Planilha gerada com sucesso. "
            "Para interpretar, utilize as colunas do relatório exibido na tabela."
        )

    try:
        dfn = df[phase_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        total = float(dfn.sum().sum())
        if total == 0.0:
            return (
                "As colunas de fases aparecem na planilha, mas o resultado está zerado neste arquivo. "
                "Isso costuma ocorrer quando o texto está muito curto ou quando as falas não trazem trechos claros das etapas."
            )
        return (
            "As fases aparecem na planilha. "
            "Revise as colunas de fases e, quando houver trechos/justificativas, valide com a transcrição."
        )
    except Exception:
        return (
            "As colunas de fases aparecem na planilha, mas não foi possível interpretar automaticamente os valores. "
            "Você pode revisar manualmente as colunas de fase e os campos de justificativa/trechos."
        )


# ==============================
# 🧩 UI helpers: resultado (VISUAL NOVO)
# ==============================
def render_result_hero(kind: str, run_id: str, subtitle: str = ""):
    kind_label = (kind or "").upper() if kind else "RESULTADO"
    subtitle = subtitle or "Avaliação concluída e pronta para revisão."

    # Pills compactas (sem aquele “card branco gigante”)
    pills = []
    if kind:
        pills.append(
            f"<span class='pill ok'><span class='dot'></span>{kind_label}</span>"
        )
    if run_id:
        pills.append(
            f"<span class='pill neutral'><span class='dot'></span>Protocolo: {run_id}</span>"
        )

    st.markdown(
        f"""
<div class="result-hero">
  <div class="left">
    <div class="icon">✅</div>
    <div>
      <p class="title">Resultado</p>
      <p class="subtitle">{subtitle}</p>
    </div>
  </div>
  <div class="pill-row">
    {''.join(pills)}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_time_card(audio_sec: float, total_sec: float):
    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">⏱️ Tempo</h3>
  <p style="margin-top:10px;margin-bottom:0;">
    <span class="pill neutral"><span class="dot"></span>Ligação <b>{human_time(audio_sec)}</b></span>
    &nbsp;&nbsp;
    <span class="pill neutral"><span class="dot"></span>Processamento <b>{human_time(total_sec)}</b></span>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_downloads_explain_individual():
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


def render_downloads_explain_batch():
    st.markdown(
        """
<div class="card">
  <h3 style="margin:0;">📥 Downloads</h3>
  <p class="smallmuted" style="margin:8px 0 0 0;">
    • <b>Excel do lote:</b> consolida todos os arquivos enviados.<br/>
    • <b>Excel individual:</b> planilha separada por arquivo (útil para auditoria).<br/>
    • <b>TXT:</b> disponível quando o envio foi por áudio.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


# ==============================
# ⏳ Progresso (UI) — visual mais clean (sem quadro branco com texto gigante)
# ==============================
def make_status_ui():
    status = st.empty()
    pbar = st.progress(0)
    timer = st.empty()

    t0 = time.time()

    def update(msg: str, p: float, est_sec: Optional[float]):
        elapsed = time.time() - t0

        if est_sec and est_sec > elapsed:
            timer.markdown(
                f"<div class='smallmuted'>⏳ Rodando há <b>{human_time(elapsed)}</b> • estimativa: <b>{human_time(est_sec)}</b></div>",
                unsafe_allow_html=True,
            )
        else:
            timer.markdown(
                f"<div class='smallmuted'>⏳ Rodando há <b>{human_time(elapsed)}</b></div>",
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
        pbar.progress(max(0, min(1, float(p))))

    def done():
        status.empty()
        timer.empty()
        pbar.empty()

    return update, done


# ==============================
# ✅ Processamento: Individual
# ==============================
def run_single_txt(txt: str):
    ok, msg = validar_transcricao(txt)
    if not ok:
        st.error(msg)
        return

    update, done = make_status_ui()
    update("Iniciando avaliação…", 0.05, None)

    fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    try:
        update("Avaliando conversa…", 0.25, None)
        zip_bytes, hdr, elapsed = vps_run_file(txt.encode("utf-8", errors="ignore"), fname, "text/plain")
        update("Abrindo planilha…", 0.95, None)
    except RuntimeError as e:
        done()
        st.error("❌ Não foi possível concluir a avaliação.")
        st.code(str(e))
        return

    done()

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
        "zip_bytes": zip_bytes,
        "files_map": files_map,
    }
    st.session_state["last_run_id"] = hdr.get("X-Run-Id", "")


def run_single_wav(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()
    audio_sec = duracao_wav_seg_bytes(wav_bytes)
    if audio_sec and audio_sec > 600:
        st.error(f"❌ Áudio tem {audio_sec/60:.1f} minutos. Limite recomendado: 10 minutos.")
        return

    update, done = make_status_ui()
    update("Iniciando avaliação…", 0.05, None)

    try:
        update("Transcrevendo áudio…", 0.25, None)
        update("Avaliando conversa…", 0.60, None)
        zip_bytes, hdr, elapsed = vps_run_file(wav_bytes, wav_file.name, "audio/wav")
        update("Abrindo planilha…", 0.95, None)
    except RuntimeError as e:
        done()
        st.error("❌ Não foi possível concluir a avaliação.")
        st.code(str(e))
        return

    done()

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
        "zip_bytes": zip_bytes,
        "files_map": files_map,
    }
    st.session_state["last_run_id"] = hdr.get("X-Run-Id", "")


# ==============================
# ✅ Processamento: Lote (até 10)
# ==============================
def run_batch_txt(files: List[Any], pasted_blocks: List[str]):
    entradas: List[Tuple[str, str]] = []

    if files:
        for f in files[:10]:
            content = f.getvalue().decode("utf-8", errors="ignore")
            entradas.append((f.name, content))

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

    update, done = make_status_ui()
    update("Iniciando lote…", 0.05, None)

    itens: List[dict] = []

    for idx, (name, txt) in enumerate(entradas, start=1):
        update(f"Avaliando {idx}/{len(entradas)}…", 0.10 + 0.80 * (idx - 1) / max(1, len(entradas)), None)
        try:
            zip_bytes, hdr, _elapsed = vps_run_file(txt.encode("utf-8", errors="ignore"), name, "text/plain")
        except RuntimeError as e:
            done()
            st.error(f"❌ Falha ao avaliar {name}")
            st.code(str(e))
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
                "kind": "txt",
                "filename": name,
                "run_id": hdr.get("X-Run-Id", ""),
                "excel_individual_name": indiv_name,
                "excel_individual_bytes": indiv_xlsx_fmt,
            }
        )

        lote_excel = None
        for nm, xb in excels:
            if "spin_resultados_lote" in nm.lower():
                lote_excel = (nm, format_excel_bytes(xb))
                break

        if lote_excel:
            st.session_state["batch_lote"] = {
                "excel_name": lote_excel[0],
                "excel_bytes": lote_excel[1],
                "df": _safe_df(excel_bytes_to_df(lote_excel[1])),
            }

    done()
    st.session_state["batch_results"] = itens
    st.session_state["last_run_id"] = (itens[-1]["run_id"] if itens else "")


def run_batch_wav(wavs: List[Any]):
    if not wavs:
        st.error("Envie pelo menos 1 WAV.")
        return
    if len(wavs) > 10:
        st.error("Limite: 10 áudios por lote.")
        return

    update, done = make_status_ui()
    update("Iniciando lote…", 0.05, None)

    itens: List[dict] = []

    for idx, wavf in enumerate(wavs[:10], start=1):
        update(f"Processando {idx}/{min(10, len(wavs))}…", 0.10 + 0.80 * (idx - 1) / max(1, min(10, len(wavs))), None)

        wav_bytes = wavf.getbuffer().tobytes()
        try:
            zip_bytes, hdr, _elapsed = vps_run_file(wav_bytes, wavf.name, "audio/wav")
        except RuntimeError as e:
            done()
            st.error(f"❌ Falha ao avaliar {wavf.name}")
            st.code(str(e))
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

        lote_excel = None
        for nm, xb in excels:
            if "spin_resultados_lote" in nm.lower():
                lote_excel = (nm, format_excel_bytes(xb))
                break
        if lote_excel:
            st.session_state["batch_lote"] = {
                "excel_name": lote_excel[0],
                "excel_bytes": lote_excel[1],
                "df": _safe_df(excel_bytes_to_df(lote_excel[1])),
            }

    done()
    st.session_state["batch_results"] = itens
    st.session_state["last_run_id"] = (itens[-1]["run_id"] if itens else "")


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
# 🧭 Sidebar (sem URLs / sem técnica)
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

    online = vps_health()
    if online:
        st.success("Servidor conectado ✅")
    else:
        st.warning("Servidor indisponível ⚠️")

    st.markdown("---")
    if st.button("🧹 Limpar", use_container_width=True, key="nav_clear_all"):
        clear_all_results()
        st.rerun()


# ==============================
# ✅ UI: Telas
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")
    tab_txt, tab_wav = st.tabs(["📝 Texto", "🎧 Áudio"])

    # -------- TXT
    with tab_txt:
        if st.session_state.get("single_tab") != "txt":
            clear_single()
            st.session_state["single_tab"] = "txt"

        st.markdown("<div class='smallmuted'>O texto deve começar as falas com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>", unsafe_allow_html=True)

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

    # -------- WAV
    with tab_wav:
        if st.session_state.get("single_tab") != "wav":
            clear_single()
            st.session_state["single_tab"] = "wav"

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
    tab_txt, tab_wav = st.tabs(["📝 Texto", "🎧 Áudio"])

    # -------- BATCH TXT
    with tab_txt:
        if st.session_state.get("batch_tab") != "txt":
            clear_batch()
            st.session_state["batch_tab"] = "txt"

        st.markdown("<div class='smallmuted'>Os textos devem começar as falas com <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>", unsafe_allow_html=True)

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

    # -------- BATCH WAV
    with tab_wav:
        if st.session_state.get("batch_tab") != "wav":
            clear_batch()
            st.session_state["batch_tab"] = "wav"

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
# (visual novo do header + pills)
# ==============================
lr = st.session_state.get("last_result")
if lr and isinstance(lr.get("df"), pd.DataFrame):
    st.markdown("---")

    df = lr["df"]
    kind = lr.get("kind", "")
    run_id = lr.get("run_id", "")

    render_result_hero(
        kind=kind,
        run_id=run_id,
        subtitle="Avaliação finalizada. Confira a planilha abaixo e faça o download quando quiser.",
    )

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

    render_downloads_explain_individual()

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
# ==============================
br = st.session_state.get("batch_results")
batch_lote = st.session_state.get("batch_lote")

if br:
    st.markdown("---")
    st.markdown("## ✅ Resultados do lote")

    if batch_lote and isinstance(batch_lote.get("df"), pd.DataFrame) and not batch_lote["df"].empty:
        st.markdown("### 📊 Planilha do lote (aberta)")
        st.dataframe(batch_lote["df"], use_container_width=True)

    render_downloads_explain_batch()

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
