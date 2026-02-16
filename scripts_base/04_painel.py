# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT + WAV)
# MODO ÚNICO: VPS OBRIGATÓRIO (Streamlit / Cloud)
# ✅ Usa 05_api_vps.py: POST {VPS_BASE_URL}/run  (multipart file=@...)
# ✅ Retorna ZIP com: excel/*.xlsx + logs + txt/json (opcional)
# ✅ Excel aparece "aberto" (DataFrame) após concluir
# ✅ Excel formatado: wrap + largura + freeze
# ✅ Sem 03 / sem pontuação
# ===============================================

import os
import re
import io
import time
import json
import zipfile
import base64
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


MODE = _get_cfg("MODE", "VPS").upper()  # VPS obrigatório
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
    st.error("❌ Este painel está em MODO ÚNICO: VPS. Ajuste MODE='VPS' nos secrets.")
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
# 🎨 Estilo profissional (mantido)
# ==============================
st.markdown(
    """
<style>
body {
  background-color: #FFFFFF;
  color: #0B1220;
  font-family: Segoe UI, Arial, sans-serif;
}
h1, h2, h3 { color: #0B63F3; }

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

.badge{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #AFC7F3 !important;
  background: #F6F9FF !important;
  color: #0B63F3 !important;
  font-weight: 900;
  font-size: 0.9rem;
}
.badge.ok{
  background: #E6FFF3 !important;
  border-color: #29B37C !important;
  color: #0B6B4B !important;
}
.badge.warn{
  background: #FFF5D6 !important;
  border-color: #D39B00 !important;
  color: #7A5600 !important;
}
.badge.bad{
  background: #FFE7EC !important;
  border-color: #E64664 !important;
  color: #9E1230 !important;
}
.smallmuted{ color:#3A4A63; font-weight:600; }
</style>
""",
    unsafe_allow_html=True,
)

# ==============================
# 📂 Diretórios temporários (painel)
# ==============================
BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "_tmp_painel"
TMP_TXT = TMP_DIR / "txt"
TMP_WAV = TMP_DIR / "wav"
TMP_DIR.mkdir(exist_ok=True)
TMP_TXT.mkdir(exist_ok=True)
TMP_WAV.mkdir(exist_ok=True)


def limpar_temporarios():
    try:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        TMP_DIR.mkdir(exist_ok=True)
        TMP_TXT.mkdir(exist_ok=True)
        TMP_WAV.mkdir(exist_ok=True)
    except Exception:
        pass


# ==============================
# ✅ Validação do TXT (simples e segura)
# ==============================
def validar_transcricao(txt: str) -> Tuple[bool, str]:
    linhas = [l.strip() for l in (txt or "").splitlines() if l.strip()]
    if len(linhas) < 4:
        return False, "Texto muito curto."
    if not any(re.match(r"^\[(VENDEDOR|CLIENTE)\]", l, re.I) for l in linhas):
        return False, "Formato inválido. Use [VENDEDOR] e [CLIENTE] no início das falas."
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
    """Formata o Excel para NÃO 'cortar' textos (wrap + largura + freeze)."""
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

    # Congela header
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
    """Normaliza tipos e garante colunas úteis se existirem."""
    if df is None or df.empty:
        return df
    df = df.copy()

    # tenta padronizar nomes comuns
    ren = {
        "arquivo": "arquivo",
        "filename": "arquivo",
        "file": "arquivo",
    }
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


def vps_run_file(file_bytes: bytes, filename: str, mime: str) -> Tuple[bytes, Dict[str, str]]:
    """
    Envia 1 arquivo para /run e recebe ZIP bytes.
    Retorna (zip_bytes, headers úteis).
    """
    files = {"file": (filename, file_bytes, mime)}
    headers = {"X-API-KEY": VPS_API_KEY}

    try:
        r = requests.post(
            f"{VPS_BASE_URL}/run",
            files=files,
            headers=headers,
            timeout=REQ_TIMEOUT,
        )
        r.raise_for_status()
        zip_bytes = r.content
        useful = {
            "X-Run-Id": r.headers.get("X-Run-Id", ""),
            "X-Debug": r.headers.get("X-Debug", ""),
        }
        return zip_bytes, useful

    except requests.exceptions.ConnectTimeout:
        raise RuntimeError(
            "ConnectTimeout: não consegui CONECTAR na VPS.\n"
            "Causas comuns: porta fechada (firewall), VPS fora do ar.\n"
            f"VPS_BASE_URL: {_pretty_url(VPS_BASE_URL)}\n"
            f"Timeout(connect/read): {CONNECT_TIMEOUT_S}s / {READ_TIMEOUT_S}s"
        )
    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            "ReadTimeout: conectei na VPS, mas ela demorou para responder.\n"
            "Aumente API_TIMEOUT_S ou use áudios menores."
        )
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "ConnectionError: falha de rede ao acessar a VPS.\n"
            f"URL: {_pretty_url(VPS_BASE_URL)}\nDetalhe: {e}"
        )
    except requests.exceptions.HTTPError:
        try:
            body = r.text[:800]
            code = r.status_code
        except Exception:
            body = "—"
            code = "—"
        raise RuntimeError(f"HTTPError: servidor respondeu com erro.\nStatus: {code}\nBody: {body}")
    except Exception as e:
        raise RuntimeError(f"Erro inesperado ao chamar VPS /run: {e}")


def zip_extract_all(zip_bytes: bytes) -> Dict[str, bytes]:
    """
    Retorna dict: {arcname: bytes}
    """
    out: Dict[str, bytes] = {}
    bio = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(bio, "r") as z:
        for name in z.namelist():
            try:
                out[name] = z.read(name)
            except Exception:
                pass
    return out


def pick_main_excels(files_map: Dict[str, bytes]) -> List[Tuple[str, bytes]]:
    """
    Retorna lista ordenada de XLSX encontrados no zip.
    Preferência: SPIN_RESULTADOS_LOTE*.xlsx primeiro.
    """
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


def make_combined_zip(items: List[Dict[str, Any]]) -> bytes:
    """
    Cria um ZIP local com os ZIPs retornados pela VPS (um por item),
    mais um arquivo resumo JSON.
    """
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as z:
        resumo = []
        for it in items:
            rid = it.get("run_id") or f"run_{it.get('idx', '')}"
            zbytes = it.get("zip_bytes")
            if zbytes:
                z.writestr(f"{rid}/{rid}.zip", zbytes)
            resumo.append({
                "run_id": rid,
                "filename": it.get("filename"),
                "kind": it.get("kind"),
                "debug": it.get("debug"),
                "created_at": it.get("created_at"),
            })
        z.writestr("RESUMO.json", json.dumps(resumo, ensure_ascii=False, indent=2))
    mem.seek(0)
    return mem.read()


# ==============================
# 🧠 Estado do app (ÚNICO)
# ==============================
if "view" not in st.session_state:
    st.session_state["view"] = "single"  # "single" | "batch"

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None  # dict padronizado

if "batch_results" not in st.session_state:
    st.session_state["batch_results"] = None  # List[dict] ou None


def set_last_result(payload: dict):
    st.session_state["last_result"] = payload


def clear_last_result():
    st.session_state["last_result"] = None


def set_batch_results(items: List[dict]):
    st.session_state["batch_results"] = items


def clear_batch_results():
    st.session_state["batch_results"] = None


# ==============================
# 🧾 Comentários simples sobre fases
# ==============================
def fase_commentary(df: pd.DataFrame) -> List[str]:
    """
    Sem pontuação: apenas comentários se colunas/fases não existirem,
    ou se todas estiverem zeradas.
    """
    if df is None or df.empty:
        return ["Sem dados para comentar (DataFrame vazio)."]

    cols = [c.lower() for c in df.columns]
    msgs = []

    # tenta detectar colunas de fase (CHECK_01.. ou P0..P4)
    has_check = any("check_" in c for c in cols)
    has_p = any(re.match(r"^p[0-4]", c) for c in cols) or any("p0" in c or "p1" in c or "p2" in c or "p3" in c or "p4" in c for c in cols)

    if not has_check and not has_p:
        msgs.append("O Excel não traz colunas explícitas de fases (P0–P4 / CHECK_*). Ainda assim, o resultado pode estar correto conforme o template do 02.")
        return msgs

    # comentários básicos se existirem
    # (não inferimos papéis — só olhamos os números)
    try:
        numeric_cols = [c for c in df.columns if str(c).lower().startswith("check_") or str(c).lower().startswith("p")]
        if numeric_cols:
            dfn = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            # se tudo NaN:
            if dfn.isna().all().all():
                msgs.append("As colunas de fase existem, mas não estão numéricas (não foi possível interpretar valores).")
            else:
                # se todas fases zeradas no lote:
                s = dfn.fillna(0).sum().sum()
                if float(s) == 0.0:
                    msgs.append("As colunas de fase estão presentes, mas o resultado está zerado (todas as fases ausentes neste(s) arquivo(s)).")
    except Exception:
        pass

    if not msgs:
        msgs.append("Fases presentes no Excel. Use a tabela abaixo para revisar o resultado por arquivo.")
    return msgs


# ==============================
# 🧩 UI helpers: cards
# ==============================
def render_card_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">{title}</h3>
  <p class="smallmuted" style="margin:6px 0 0 0;">{subtitle}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_badges(run_id: str = "", debug: str = "", kind: str = ""):
    parts = []
    if kind:
        parts.append(f'<span class="badge ok">{kind.upper()}</span>')
    if run_id:
        parts.append(f'<span class="badge">Run: {run_id}</span>')
    if debug:
        parts.append(f'<span class="badge warn" title="{debug}">Debug</span>')

    st.markdown(
        f"""
<div class="card">
  <p style="margin:0;">{"&nbsp;&nbsp;".join(parts) if parts else "—"}</p>
</div>
""",
        unsafe_allow_html=True,
    )


# ==============================
# ✅ Processamento: SINGLE
# ==============================
def processar_txt_unico(txt: str, fname: str):
    ok, msg = validar_transcricao(txt)
    if not ok:
        st.error(msg)
        return

    t0 = time.time()
    try:
        with st.spinner("Enviando para a VPS e gerando Excel…"):
            zip_bytes, hdr = vps_run_file(txt.encode("utf-8", errors="ignore"), fname, "text/plain")
    except RuntimeError as e:
        st.error("❌ Falha ao chamar a VPS.")
        st.code(str(e))
        return

    total_sec = time.time() - t0
    files_map = zip_extract_all(zip_bytes)
    excels = pick_main_excels(files_map)

    if not excels:
        st.error("❌ A VPS retornou ZIP, mas não encontrei nenhum .xlsx dentro.")
        st.caption("Arquivos no ZIP:")
        st.write(list(files_map.keys())[:200])
        return

    # escolhe principal para exibir
    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)
    df = _safe_df(excel_bytes_to_df(main_xlsx_fmt))

    payload = {
        "kind": "txt",
        "filename": fname,
        "zip_bytes": zip_bytes,
        "run_id": hdr.get("X-Run-Id", ""),
        "debug": hdr.get("X-Debug", ""),
        "excels": excels,  # lista de (name, bytes)
        "main_excel_name": main_name,
        "main_excel_bytes": main_xlsx_fmt,
        "df": df,
        "timings": {"audio_sec": 0.0, "total_sec": float(total_sec)},
        "files_map_names": list(files_map.keys()),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    set_last_result(payload)
    st.success(f"✅ Concluído em {human_time(total_sec)}")


def processar_wav_unico(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()
    audio_sec = duracao_wav_seg_bytes(wav_bytes)

    if audio_sec and audio_sec > 600:
        st.error(f"❌ Áudio tem {audio_sec/60:.1f} minutos. Limite recomendado: 10 minutos.")
        return

    t0 = time.time()
    try:
        with st.spinner("Enviando para a VPS (transcrição + avaliação + Excel)…"):
            zip_bytes, hdr = vps_run_file(wav_bytes, wav_file.name, "audio/wav")
    except RuntimeError as e:
        st.error("❌ Falha ao chamar a VPS.")
        st.code(str(e))
        return

    total_sec = time.time() - t0
    files_map = zip_extract_all(zip_bytes)
    excels = pick_main_excels(files_map)

    if not excels:
        st.error("❌ A VPS retornou ZIP, mas não encontrei nenhum .xlsx dentro.")
        st.caption("Arquivos no ZIP:")
        st.write(list(files_map.keys())[:200])
        return

    main_name, main_xlsx = excels[0]
    main_xlsx_fmt = format_excel_bytes(main_xlsx)
    df = _safe_df(excel_bytes_to_df(main_xlsx_fmt))

    payload = {
        "kind": "wav",
        "filename": wav_file.name,
        "zip_bytes": zip_bytes,
        "run_id": hdr.get("X-Run-Id", ""),
        "debug": hdr.get("X-Debug", ""),
        "excels": excels,
        "main_excel_name": main_name,
        "main_excel_bytes": main_xlsx_fmt,
        "df": df,
        "timings": {"audio_sec": float(audio_sec or 0.0), "total_sec": float(total_sec)},
        "files_map_names": list(files_map.keys()),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    set_last_result(payload)
    st.success(f"✅ Concluído em {human_time(total_sec)}")


# ==============================
# ✅ Processamento: BATCH (até 10)
# ==============================
def processar_lote_txt(entradas: List[Tuple[str, str]]):
    if len(entradas) > 10:
        st.error("Limite: 10 entradas por lote.")
        return

    itens: List[dict] = []
    started = time.time()

    for idx, (name, txt) in enumerate(entradas, start=1):
        ok, msg = validar_transcricao(txt)
        if not ok:
            st.error(f"❌ {name}: {msg}")
            return

        t0 = time.time()
        try:
            with st.spinner(f"Processando {idx}/{len(entradas)} na VPS…"):
                zip_bytes, hdr = vps_run_file(txt.encode("utf-8", errors="ignore"), name, "text/plain")
        except RuntimeError as e:
            st.error(f"❌ Falha ao processar {name}")
            st.code(str(e))
            return

        total_sec = time.time() - t0
        files_map = zip_extract_all(zip_bytes)
        excels = pick_main_excels(files_map)

        # principal DF
        df = pd.DataFrame()
        main_excel_name = ""
        main_excel_bytes = b""
        if excels:
            main_excel_name, main_xlsx = excels[0]
            main_excel_bytes = format_excel_bytes(main_xlsx)
            df = _safe_df(excel_bytes_to_df(main_excel_bytes))

        itens.append(
            {
                "idx": idx,
                "kind": "txt",
                "filename": name,
                "zip_bytes": zip_bytes,
                "run_id": hdr.get("X-Run-Id", ""),
                "debug": hdr.get("X-Debug", ""),
                "excels": excels,
                "main_excel_name": main_excel_name,
                "main_excel_bytes": main_excel_bytes,
                "df": df,
                "timings": {"audio_sec": 0.0, "total_sec": float(total_sec)},
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "files_map_names": list(files_map.keys()),
            }
        )

    set_batch_results(itens)
    st.success(f"✅ Lote concluído em {human_time(time.time() - started)}")


def processar_lote_wav(wavs):
    if len(wavs) > 10:
        st.error("Limite: 10 WAVs por lote.")
        return

    itens: List[dict] = []
    started = time.time()

    for idx, wavf in enumerate(wavs, start=1):
        wav_bytes = wavf.getbuffer().tobytes()
        audio_sec = duracao_wav_seg_bytes(wav_bytes)

        t0 = time.time()
        try:
            with st.spinner(f"Processando {idx}/{len(wavs)} na VPS…"):
                zip_bytes, hdr = vps_run_file(wav_bytes, wavf.name, "audio/wav")
        except RuntimeError as e:
            st.error(f"❌ Falha ao processar {wavf.name}")
            st.code(str(e))
            return

        total_sec = time.time() - t0
        files_map = zip_extract_all(zip_bytes)
        excels = pick_main_excels(files_map)

        df = pd.DataFrame()
        main_excel_name = ""
        main_excel_bytes = b""
        if excels:
            main_excel_name, main_xlsx = excels[0]
            main_excel_bytes = format_excel_bytes(main_xlsx)
            df = _safe_df(excel_bytes_to_df(main_excel_bytes))

        itens.append(
            {
                "idx": idx,
                "kind": "wav",
                "filename": wavf.name,
                "zip_bytes": zip_bytes,
                "run_id": hdr.get("X-Run-Id", ""),
                "debug": hdr.get("X-Debug", ""),
                "excels": excels,
                "main_excel_name": main_excel_name,
                "main_excel_bytes": main_excel_bytes,
                "df": df,
                "timings": {"audio_sec": float(audio_sec or 0.0), "total_sec": float(total_sec)},
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "files_map_names": list(files_map.keys()),
            }
        )

    set_batch_results(itens)
    st.success(f"✅ Lote concluído em {human_time(time.time() - started)}")


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
# 🧭 Sidebar (sem URLs)
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")

    if st.button("👤 Avaliação Individual", use_container_width=True, key="nav_single"):
        st.session_state["view"] = "single"
        st.rerun()

    if st.button("📊 Visão Gerencial", use_container_width=True, key="nav_batch"):
        st.session_state["view"] = "batch"
        st.rerun()

    st.markdown("---")

    online = vps_health()
    if online:
        st.success("Servidor VPS conectado ✅")
    else:
        st.warning("Servidor VPS indisponível ⚠️")

    st.markdown("---")
    if st.session_state.get("last_result") is not None:
        if st.button("🧹 Limpar resultado (individual)", use_container_width=True, key="nav_clear_result"):
            clear_last_result()
            st.rerun()

    if st.session_state.get("batch_results") is not None:
        if st.button("🧹 Limpar resultados (lote)", use_container_width=True, key="nav_clear_batch"):
            clear_batch_results()
            st.rerun()


# ==============================
# ✅ UI: Telas
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")
    tab_txt, tab_wav = st.tabs(["📝 Colar transcrição (TXT)", "🎧 Enviar áudio (WAV)"])

    # -------- TXT (single)
    with tab_txt:
        exemplo = (
            "[VENDEDOR] Olá, bom dia! Aqui é o Carlos, da MedTech Solutions. Tudo bem?\n"
            "[CLIENTE] Bom dia! Tudo bem.\n"
            "[VENDEDOR] Hoje, como vocês controlam os materiais e implantes? É planilha, sistema ou um processo fixo?\n"
            "[CLIENTE] A gente usa planilhas.\n"
        )

        txt_input = st.text_area(
            "Cole a transcrição aqui",
            height=260,
            value=exemplo,
            key="txt_input_single",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Enviar para VPS e gerar Excel", use_container_width=True, key="btn_eval_txt_single"):
                limpar_temporarios()
                clear_last_result()
                fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                processar_txt_unico(txt_input, fname)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_txt_single"):
                clear_last_result()
                st.rerun()

    # -------- WAV (single)
    with tab_wav:
        up_wav = st.file_uploader(
            "Envie um WAV (até ~10 min)",
            type=["wav"],
            accept_multiple_files=False,
            key="uploader_wav_single",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Enviar para VPS (01→02) e gerar Excel", use_container_width=True, key="btn_eval_wav_single"):
                if up_wav is None:
                    st.error("Envie um WAV para continuar.")
                else:
                    limpar_temporarios()
                    clear_last_result()
                    processar_wav_unico(up_wav)

        with colB:
            if st.button("🧹 Limpar", use_container_width=True, key="btn_clear_wav_single"):
                clear_last_result()
                st.rerun()

else:
    st.markdown("### 📊 Visão Gerencial (até 10)")
    st.info("Em lote, cada arquivo é processado na VPS e você pode baixar Excel/ZIP por item, ou tudo junto ✅")

    modo = st.selectbox(
        "Tipo de entrada",
        ["TXT (arquivos .txt ou colar vários)", "WAV (áudios .wav)"],
        index=0,
        key="select_modo_batch",
    )
    st.markdown("---")

    if modo.startswith("TXT"):
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
        )

        if st.button("✅ Rodar lote (TXT) na VPS", use_container_width=True, key="btn_run_batch_txt"):
            entradas: List[Tuple[str, str]] = []

            if up_txts:
                for f in up_txts[:10]:
                    content = f.getvalue().decode("utf-8", errors="ignore")
                    entradas.append((f.name, content))

            if multi_txt.strip():
                blocos = [b.strip() for b in multi_txt.split("\n---\n") if b.strip()]
                for i, b in enumerate(blocos[:10], start=1):
                    entradas.append((f"colado_{i}.txt", b))

            if not entradas:
                st.error("Envie TXT(s) ou cole pelo menos um bloco.")
            else:
                limpar_temporarios()
                clear_batch_results()
                processar_lote_txt(entradas)

    else:
        up_wavs = st.file_uploader(
            "Envie até 10 WAVs",
            type=["wav"],
            accept_multiple_files=True,
            key="uploader_wav_batch",
        )

        if st.button("✅ Rodar lote (WAV) na VPS", use_container_width=True, key="btn_run_batch_wav"):
            if not up_wavs:
                st.error("Envie pelo menos 1 WAV.")
            else:
                limpar_temporarios()
                clear_batch_results()
                processar_lote_wav(up_wavs)


# ==============================
# ✅ Resultado persistente (individual) + downloads
# ==============================
lr = st.session_state.get("last_result")
if lr and isinstance(lr.get("df"), pd.DataFrame):
    st.markdown("---")
    st.markdown("## ✅ Resultado atual (individual)")

    kind = lr.get("kind", "")
    run_id = lr.get("run_id", "")
    debug = lr.get("debug", "")
    filename = lr.get("filename", "")
    timings = lr.get("timings", {}) or {}

    render_badges(run_id=run_id, debug=debug, kind=kind)

    # tempos (sem pontuação)
    audio_sec = float(timings.get("audio_sec", 0) or 0)
    total_sec = float(timings.get("total_sec", 0) or 0)

    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">⏱️ Tempos</h3>
  <p style="margin-top:10px;margin-bottom:0;">
    <span class="badge">Ligação</span> <b>{human_time(audio_sec)}</b>
    &nbsp;&nbsp;&nbsp;
    <span class="badge">Total</span> <b>{human_time(total_sec)}</b>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # comentários sobre fases
    df = lr["df"]
    comments = fase_commentary(df)
    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">Comentários</h3>
  <ul style="margin-top:10px;margin-bottom:0;">
    {''.join([f"<li>{c}</li>" for c in comments])}
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 Excel (aberto)")
    st.dataframe(df, use_container_width=True)

    st.markdown("### 📥 Downloads")
    base = Path(filename).stem if filename else f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # download ZIP completo
    st.download_button(
        "📦 Baixar ZIP completo (VPS)",
        data=lr.get("zip_bytes", b""),
        file_name=f"{base}_resultado.zip",
        mime="application/zip",
        use_container_width=True,
        key=f"dl_zip_single_{base}",
    )

    # download XLSX principal já formatado
    main_xlsx = lr.get("main_excel_bytes", b"")
    if main_xlsx:
        st.download_button(
            "📥 Baixar Excel principal (formatado)",
            data=main_xlsx,
            file_name=f"{base}_avaliacao_spin.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_main_xlsx_single_{base}",
        )

    # se houver múltiplos excels no zip, lista para baixar
    excels = lr.get("excels") or []
    if len(excels) > 1:
        st.markdown("#### Outros Excel(s) no ZIP")
        for i, (nm, xb) in enumerate(excels[1:], start=1):
            xb_fmt = format_excel_bytes(xb)
            short = Path(nm).name
            st.download_button(
                f"📥 Baixar: {short}",
                data=xb_fmt,
                file_name=short,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"dl_other_xlsx_{base}_{i}",
            )

# ==============================
# ✅ Resultados do LOTE + downloads por item + ZIP combinado
# ==============================
br = st.session_state.get("batch_results")
if br:
    st.markdown("---")
    st.markdown("## ✅ Resultados (lote) — Excel aberto + downloads")

    # ZIP combinado de todos os itens
    combined_zip = make_combined_zip(br)
    st.download_button(
        "📦 Baixar tudo (ZIP combinado do lote)",
        data=combined_zip,
        file_name=f"lote_resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mime="application/zip",
        use_container_width=True,
        key="dl_combined_zip_batch",
    )

    for item in br:
        idx = item.get("idx", 0)
        filename = str(item.get("filename") or f"item_{idx}")
        base = Path(filename).stem
        run_id = item.get("run_id", "")
        debug = item.get("debug", "")
        kind = item.get("kind", "")
        df = item.get("df")

        with st.expander(f"📌 {idx}. {filename}", expanded=False):
            render_badges(run_id=run_id, debug=debug, kind=kind)

            # comentários sobre fases
            if isinstance(df, pd.DataFrame) and not df.empty:
                comments = fase_commentary(df)
                st.markdown(
                    f"""
<div class="card">
  <h3 style="margin:0;">Comentários</h3>
  <ul style="margin-top:10px;margin-bottom:0;">
    {''.join([f"<li>{c}</li>" for c in comments])}
  </ul>
</div>
""",
                    unsafe_allow_html=True,
                )

                st.markdown("### 📊 Excel (aberto)")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Não foi possível abrir o Excel deste item (sem .xlsx no ZIP ou leitura falhou).")

            st.markdown("### 📥 Downloads do item")

            # ZIP original do item
            st.download_button(
                "📦 Baixar ZIP (VPS) deste item",
                data=item.get("zip_bytes", b""),
                file_name=f"{base}_resultado.zip",
                mime="application/zip",
                use_container_width=True,
                key=f"dl_zip_item_{idx}_{base}",
            )

            # XLSX principal formatado
            main_xlsx = item.get("main_excel_bytes", b"")
            if main_xlsx:
                st.download_button(
                    "📥 Baixar Excel principal (formatado)",
                    data=main_xlsx,
                    file_name=f"{base}_avaliacao_spin.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_xlsx_item_{idx}_{base}",
                )

# ==============================
# 🧾 Rodapé (mantido)
# ==============================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3A4A63;'>"
    "SPIN Analyzer — Projeto Tele_IA 2026 | Desenvolvido por Paulo Coutinho"
    "</div>",
    unsafe_allow_html=True,
)
