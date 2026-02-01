# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT + WAV)
# MODO ÚNICO: VPS OBRIGATÓRIO (Streamlit / Cloud)
# ✅ Código UNIFICADO (sem duplicações) + keys em widgets
# ✅ Parte 1/2: BASE + Helpers + Scoring + Render (sem UI principal ainda)
# ✅ + Tratamento robusto de ConnectTimeout/ReadTimeout
# ✅ + Preparação para batch com downloads por item (Parte 2)
# ===============================================

import os
import re
import time
import json
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
# ⚙️ Configurações (Secrets/Env)
# ==============================
ANALYZE_API_URL = os.getenv("ANALYZE_API_URL", "").strip()
TRANSCRIBE_API_URL = os.getenv("TRANSCRIBE_API_URL", "").strip()

CONNECT_TIMEOUT_S = int(os.getenv("CONNECT_TIMEOUT_S", "10"))
READ_TIMEOUT_S = int(os.getenv("API_TIMEOUT_S", "7200"))
REQ_TIMEOUT = (CONNECT_TIMEOUT_S, READ_TIMEOUT_S)

if not ANALYZE_API_URL:
    st.error("❌ ANALYZE_API_URL não configurado (Secrets/Env).")
    st.stop()

if not TRANSCRIBE_API_URL:
    st.error("❌ TRANSCRIBE_API_URL não configurado (Secrets/Env).")
    st.stop()


def _pretty_url(u: str) -> str:
    u = (u or "").strip()
    return u


# ==============================
# 🎨 Estilo profissional
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
# 📂 Diretórios temporários
# ==============================
BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "_tmp_painel"
TMP_TXT = TMP_DIR / "txt"
TMP_WAV = TMP_DIR / "wav"
TMP_DIR.mkdir(exist_ok=True)
TMP_TXT.mkdir(exist_ok=True)
TMP_WAV.mkdir(exist_ok=True)


def limpar_temporarios():
    """Limpa a pasta temporária do painel (não afeta o servidor)."""
    try:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        TMP_DIR.mkdir(exist_ok=True)
        TMP_TXT.mkdir(exist_ok=True)
        TMP_WAV.mkdir(exist_ok=True)
    except Exception:
        pass


# ==============================
# 🌐 API — VPS (robusta)
# ==============================
def api_analyze_text(text: str, filename: str) -> dict:
    payload = {"text": text, "filename": filename}
    try:
        r = requests.post(
            ANALYZE_API_URL,
            json=payload,
            timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S),
        )
        r.raise_for_status()
        return r.json()

    except requests.exceptions.ConnectTimeout:
        raise RuntimeError(
            "ConnectTimeout: não consegui CONECTAR na API de avaliação.\n"
            "Causas comuns: porta fechada (firewall), API rodando em 127.0.0.1, servidor fora do ar.\n"
            f"ANALYZE_API_URL: {_pretty_url(ANALYZE_API_URL)}"
        )
    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            "ReadTimeout: conectei na API, mas ela demorou para responder.\n"
            "Aumente READ_TIMEOUT_S/API_TIMEOUT_S ou otimize o endpoint."
        )
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "ConnectionError: falha de rede ao acessar a API.\n"
            "Pode ser DNS, porta bloqueada, TLS/HTTPS, ou servidor fora do ar.\n"
            f"URL: {_pretty_url(ANALYZE_API_URL)}\nDetalhe: {e}"
        )
    except requests.exceptions.HTTPError:
        try:
            body = r.text[:800]
            code = r.status_code
        except Exception:
            body = "—"
            code = "—"
        raise RuntimeError(
            f"HTTPError: servidor respondeu com erro HTTP.\nStatus: {code}\nBody: {body}"
        )
    except Exception as e:
        raise RuntimeError(f"Erro inesperado ao chamar ANALYZE_API_URL: {e}")


def api_transcribe_wav(wav_bytes: bytes, filename: str) -> dict:
    files = {"file": (filename, wav_bytes, "audio/wav")}
    try:
        r = requests.post(
            TRANSCRIBE_API_URL,
            files=files,
            timeout=(CONNECT_TIMEOUT_S, READ_TIMEOUT_S),
        )
        r.raise_for_status()
        return r.json()

    except requests.exceptions.ConnectTimeout:
        raise RuntimeError(
            "ConnectTimeout: não consegui CONECTAR na API de transcrição.\n"
            "Causas comuns: porta fechada (firewall), API em 127.0.0.1, servidor fora do ar.\n"
            f"TRANSCRIBE_API_URL: {_pretty_url(TRANSCRIBE_API_URL)}"
        )
    except requests.exceptions.ReadTimeout:
        raise RuntimeError(
            "ReadTimeout: conectei na API de transcrição, mas ela demorou para responder.\n"
            "Aumente READ_TIMEOUT_S/API_TIMEOUT_S ou reduza o tamanho do áudio."
        )
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "ConnectionError: falha de rede ao acessar a API de transcrição.\n"
            f"URL: {_pretty_url(TRANSCRIBE_API_URL)}\nDetalhe: {e}"
        )
    except requests.exceptions.HTTPError:
        try:
            body = r.text[:800]
            code = r.status_code
        except Exception:
            body = "—"
            code = "—"
        raise RuntimeError(
            f"HTTPError: servidor respondeu com erro.\nStatus: {code}\nBody: {body}"
        )
    except Exception as e:
        raise RuntimeError(f"Erro inesperado ao chamar TRANSCRIBE_API_URL: {e}")


# ==============================
# ✅ Validação do TXT
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
def duracao_wav_seg(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def human_time(sec: float) -> str:
    try:
        sec = float(sec)
    except Exception:
        sec = 0.0
    if sec < 60:
        return f"{int(sec)}s"
    return f"{int(sec // 60)}m {int(sec % 60)}s"


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
# 📦 Helpers: Excel do retorno
# ==============================
def decode_excel_base64_to_bytes(excel_b64: str) -> bytes:
    return base64.b64decode(excel_b64.encode("utf-8"))


def excel_bytes_to_df(excel_bytes: bytes) -> pd.DataFrame:
    import io
    bio = io.BytesIO(excel_bytes)
    return pd.read_excel(bio)


def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "arquivo" not in df.columns:
        df["arquivo"] = ""

    df.rename(
        columns={
            "implicacao_feedback": "implication_feedback",
            "necessidade_feedback": "need_payoff_feedback",
        },
        inplace=True,
    )

    for col in [
        "abertura_nota_humana",
        "situation_nota_humana",
        "problem_nota_humana",
        "implication_nota_humana",
        "need_payoff_nota_humana",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def pick_row_by_file(df: pd.DataFrame, filename: str) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    dff = df[df["arquivo"].astype(str) == str(filename)]
    if dff.empty:
        return None
    return dff.iloc[-1]


# ==============================
# 📏 Excel: formatar largura + wrap text
# ==============================
from io import BytesIO

EXCEL_WRAP_TEXT = os.getenv("EXCEL_WRAP_TEXT", "1").strip() not in ("0", "false", "False", "")
EXCEL_DEFAULT_COL_W = int(os.getenv("EXCEL_DEFAULT_COL_W", "22"))
EXCEL_TEXT_COL_W = int(os.getenv("EXCEL_TEXT_COL_W", "55"))
EXCEL_MAX_COL_W = int(os.getenv("EXCEL_MAX_COL_W", "80"))


def format_excel_bytes(excel_bytes: bytes) -> bytes:
    """Formata o Excel retornado pela API para NÃO 'cortar' textos."""
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

    long_text_markers = ("_texto", "_feedback", "justific", "trecho", "observ", "coment", "resumo")

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


# ==============================
# 🧩 Scoring + UI helpers
# ==============================
def clamp_int(x, lo=0, hi=5, default=0):
    try:
        v = int(float(x))
        return max(lo, min(hi, v))
    except Exception:
        return default


def build_phase_scores_from_row(row: pd.Series) -> dict:
    return {
        "abertura": clamp_int(row.get("abertura_nota_humana", 0)),
        "situation": clamp_int(row.get("situation_nota_humana", 0)),
        "problem": clamp_int(row.get("problem_nota_humana", 0)),
        "implication": clamp_int(row.get("implication_nota_humana", 0)),
        "need_payoff": clamp_int(row.get("need_payoff_nota_humana", 0)),
    }


def score_total_25(phase_scores: dict) -> int:
    return sum(int(phase_scores.get(k, 0)) for k in ["abertura", "situation", "problem", "implication", "need_payoff"])


def label_qualidade_por_score25(score25: int) -> Tuple[str, str]:
    if score25 <= 4:
        return "Crítica", "bad"
    if score25 <= 10:
        return "Baixa", "bad"
    if score25 <= 14:
        return "Moderada", "warn"
    if score25 <= 18:
        return "Boa", "ok"
    return "Excelente", "ok"


def msg_geral_por_score25(score25: int) -> str:
    if score25 <= 6:
        return (
            "A pontuação indica uma execução muito fraca do método SPIN. "
            "A conversa se manteve predominantemente reativa e operacional, "
            "com ausência de enquadramento claro e pouco ou nenhum diagnóstico estruturado."
        )
    if score25 <= 12:
        return (
            "A avaliação revela sinais iniciais de estrutura consultiva, porém com execução instável. "
            "Algumas etapas aparecem pontualmente, mas sem profundidade ou encadeamento."
        )
    if score25 <= 18:
        return (
            "A conversa apresenta uma boa base do método SPIN. "
            "Há direcionamento e início de diagnóstico consultivo, com oportunidades claras de evolução."
        )
    if score25 <= 23:
        return "Execução forte e consistente do método SPIN, com bom encadeamento e exploração adequada de impacto."
    return (
        "Excelente execução do método SPIN, com enquadramento claro desde a abertura, "
        "diagnóstico progressivo e conexão forte entre impacto e valor."
    )


def ranking_por_nota(nota: int) -> str:
    if nota <= 0:
        return "Ausente"
    if nota <= 2:
        return "Iniciante"
    if nota == 3:
        return "Intermediário"
    if nota == 4:
        return "Bom"
    return "Excelente"


def badge_class_por_nota(nota: int) -> str:
    if nota >= 4:
        return "ok"
    if nota == 3:
        return "warn"
    return "bad"


def feedback_programado(fase: str, nota: int) -> str:
    base = {
        "abertura": [
            "Abertura ausente. Não houve enquadramento mínimo (quem liga, por quê, objetivo e tempo).",
            "Abertura fraca. Houve contato inicial, mas faltou alinhar contexto e agenda.",
            "Abertura adequada, porém incompleta. Explicite objetivo e valide disponibilidade.",
            "Boa abertura. Melhore confirmando papel do interlocutor e combinando agenda curta.",
            "Abertura forte. Consolide agenda+tempo e peça permissão para conduzir perguntas-chave.",
            "Abertura excelente. Enquadramento completo com transição natural para diagnóstico."
        ],
        "situation": [
            "Situação ausente. Não foi coletado o cenário atual.",
            "Situação superficial. Faltam elementos básicos (processo, ferramentas, frequência).",
            "Situação básica. Evolua quantificando volume/tempo e pedindo exemplo real.",
            "Boa Situação. Eleve registrando números e resumindo para confirmação.",
            "Situação muito boa. Explore exceções e pontos de controle.",
            "Situação excelente. Contexto completo para sustentar as próximas fases."
        ],
        "problem": [
            "Problema ausente. Não explicitou uma dor concreta.",
            "Problema fraco. Dor sugerida sem evidências. Peça exemplos e frequência.",
            "Problema identificado, porém raso. Priorize 1–2 dores e aprofunde follow-ups.",
            "Boa etapa de Problema. Transforme dor em requisito objetivo e valide prioridade.",
            "Problema forte. Estime custo/tempo e defina critério de “resolvido”.",
            "Problema excelente. Dores bem definidas e priorizadas com exemplos."
        ],
        "implication": [
            "Implicação ausente. Não explorou consequências (custo/risco/qualidade).",
            "Implicação fraca. Impacto genérico. Detalhe consequências e quem é afetado.",
            "Implicação presente. Quantifique e conecte a metas/indicadores.",
            "Boa Implicação. Aprofunde 1–2 impactos com números e exemplos.",
            "Implicação forte. Resuma impacto e obtenha confirmação explícita.",
            "Implicação excelente. Impacto claro, coerente e sustentado."
        ],
        "need_payoff": [
            "Need-payoff ausente. Não consolidou valor nem próximos passos.",
            "Benefícios genéricos. Conecte valor diretamente à dor/impacto.",
            "Need-payoff adequado. Explicite ganhos e defina critério de sucesso.",
            "Boa etapa. Confirme prioridade e desenhe próximos passos objetivos.",
            "Need-payoff forte. Faça resumo dor→impacto→valor e feche compromisso.",
            "Need-payoff excelente. Valor consolidado, decisão e próximos passos claros."
        ],
    }
    arr = base.get(fase, ["—"] * 6)
    try:
        n = int(nota)
    except Exception:
        n = 0
    n = max(0, min(5, n))
    return arr[n]


def render_avaliacao_completa(row: pd.Series):
    """Render detalhamento (sem widgets)."""
    phase_scores = build_phase_scores_from_row(row)
    score25 = score_total_25(phase_scores)
    qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)
    msg_geral = msg_geral_por_score25(score25)
    processado_em = str(row.get("processado_em", row.get("avaliado_em", "—")))

    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">Resumo</h3>
  <p style="margin-top:6px;margin-bottom:10px;">
    <span class="badge {qualidade_tag}">{qualidade_label}</span>
    &nbsp;&nbsp; <b>Pontuação:</b> {score25}/25
    &nbsp;&nbsp; <b>Data/Hora:</b> {processado_em}
  </p>
  <p style="margin:0;">{msg_geral}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    criterios = [
        ("abertura", "Abertura"),
        ("situation", "Situação"),
        ("problem", "Problema"),
        ("implication", "Implicação"),
        ("need_payoff", "Necessidade-benefício"),
    ]

    for key, label in criterios:
        nota = phase_scores[key]
        rank = ranking_por_nota(nota)
        bc = badge_class_por_nota(nota)
        fb = feedback_programado(key, nota)

        st.markdown(
            f"""
<div class="card">
  <h3 style="margin:0;">{label}</h3>
  <p style="margin-top:6px;margin-bottom:10px;">
    <span class="badge {bc}">{nota}/5</span>
    &nbsp;&nbsp; <b>Ranking:</b> {rank}
  </p>
  <p style="margin:0;">{fb}</p>
</div>
""",
            unsafe_allow_html=True,
        )


def render_header_score_only(filename: str, row: pd.Series, timings: Optional[dict] = None):
    """Cabeçalho com pontuação em destaque."""
    phase_scores = build_phase_scores_from_row(row)
    score25 = score_total_25(phase_scores)
    qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)

    st.markdown(
        f"""
<div class="card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:14px;">
    <div>
      <div class="badge {qualidade_tag}" style="margin-bottom:8px;">{qualidade_label}</div>
      <div style="font-size:44px;font-weight:900;line-height:1;margin:0;color:#0B1220;">
        {score25}<span style="font-size:22px;font-weight:800;">/25</span>
      </div>
      <div class="smallmuted" style="margin-top:8px;">
        Pontuação SPIN (Abertura + Situação + Problema + Implicação + Need-payoff)
      </div>
    </div>
    <div style="text-align:right;">
      <div class="smallmuted" style="font-weight:800;margin-bottom:6px;">Identificador</div>
      <div class="badge" title="{filename}">{filename}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if timings:
        audio_sec = float(timings.get("audio_sec", 0) or 0)
        transcribe_sec = float(timings.get("transcribe_sec", 0) or 0)
        eval_sec = float(timings.get("eval_sec", 0) or 0)
        total_sec = float(timings.get("total_sec", 0) or (transcribe_sec + eval_sec))

        def _ratio_str(x, base):
            if base <= 0:
                return "—"
            return f"{(x / base):.2f}x"

        st.markdown(
            f"""
<div class="card">
  <h3 style="margin:0;">⏱️ Tempos (comparado à duração da ligação)</h3>
  <p style="margin-top:10px;margin-bottom:0;">
    <span class="badge">Ligação</span> <b>{human_time(audio_sec)}</b>
    &nbsp;&nbsp;&nbsp;
    <span class="badge">Transcrição</span> <b>{human_time(transcribe_sec)}</b> (<b>{_ratio_str(transcribe_sec, audio_sec)}</b>)
    &nbsp;&nbsp;&nbsp;
    <span class="badge">Avaliação</span> <b>{human_time(eval_sec)}</b> (<b>{_ratio_str(eval_sec, audio_sec)}</b>)
    &nbsp;&nbsp;&nbsp;
    <span class="badge">Total</span> <b>{human_time(total_sec)}</b> (<b>{_ratio_str(total_sec, audio_sec)}</b>)
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
# ===============================================
# ✅ PARTE 2/2 — UI + Execuções + Batch + Downloads por item
# ===============================================

# ==============================
# ✅ Execuções: 1 item (TXT/WAV) com tratamento de erro
# ==============================
def processar_txt_unico(txt: str, fname: str):
    started = time.time()
    try:
        with st.spinner("Avaliando no servidor (VPS)…"):
            resp = api_analyze_text(txt.strip(), filename=fname)
    except RuntimeError as e:
        st.error("❌ Falha ao chamar a API de avaliação.")
        st.code(str(e))
        return

    if not isinstance(resp, dict) or not resp.get("ok"):
        st.error("❌ O servidor não conseguiu avaliar este texto.")
        st.json(resp)
        return

    excel_b64 = resp.get("excel_base64")
    if not excel_b64:
        st.error("❌ O servidor respondeu ok, mas não retornou excel_base64.")
        st.json(resp)
        return

    excel_bytes_raw = decode_excel_base64_to_bytes(excel_b64)
    excel_bytes = format_excel_bytes(excel_bytes_raw)
    elapsed_eval = time.time() - started

    df = normalizar_df(excel_bytes_to_df(excel_bytes))
    arquivo_foco = str(resp.get("arquivo", fname))

    row = pick_row_by_file(df, arquivo_foco)
    if row is None:
        row = df.iloc[-1] if not df.empty else None

    if row is None:
        st.error("❌ Não foi possível localizar a linha do resultado.")
        st.dataframe(df, use_container_width=True)
        return

    payload = {
        "kind": "txt",
        "filename": arquivo_foco,
        "excel_bytes": excel_bytes,
        "df": df,
        "row": row,
        "timings": {
            "audio_sec": 0.0,
            "transcribe_sec": 0.0,
            "eval_sec": float(elapsed_eval),
            "total_sec": float(elapsed_eval),
        },
        "text_labeled": None,
        "transcribe_json": None,
        "original_wav_name": None,
    }
    set_last_result(payload)
    st.success(f"✅ Avaliação concluída em {human_time(elapsed_eval)}")


def processar_wav_unico(wav_file):
    t0_total = time.time()
    wav_bytes = wav_file.getbuffer().tobytes()

    tmp_wav = TMP_WAV / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    tmp_wav.write_bytes(wav_bytes)

    try:
        audio_sec = duracao_wav_seg(tmp_wav)
    except Exception:
        audio_sec = 0.0

    if audio_sec > 600:
        st.error(f"❌ Áudio tem {audio_sec/60:.1f} minutos. Limite recomendado: 10 minutos.")
        return

    # Transcrição
    t0_trans = time.time()
    try:
        with st.spinner("Transcrevendo no servidor (VPS)…"):
            data_t = api_transcribe_wav(wav_bytes, filename=wav_file.name)
    except RuntimeError as e:
        st.error("❌ Falha ao chamar a API de transcrição.")
        st.code(str(e))
        return

    transcribe_sec = time.time() - t0_trans

    text_labeled = (data_t.get("text_labeled") or "").strip()
    if not text_labeled:
        st.error("❌ A transcrição veio vazia.")
        st.json(data_t)
        return

    # Avaliação
    fname = f"{Path(wav_file.name).stem}.txt"
    t0_eval = time.time()
    try:
        with st.spinner("Avaliando no servidor (VPS)…"):
            resp = api_analyze_text(text_labeled, filename=fname)
    except RuntimeError as e:
        st.error("❌ Falha ao chamar a API de avaliação.")
        st.code(str(e))
        return

    eval_sec = time.time() - t0_eval

    if not resp.get("ok"):
        st.error("❌ O servidor não conseguiu avaliar este áudio.")
        st.json(resp)
        return

    excel_b64 = resp.get("excel_base64")
    if not excel_b64:
        st.error("❌ O servidor respondeu ok, mas não retornou excel_base64.")
        st.json(resp)
        return

    excel_bytes_raw = decode_excel_base64_to_bytes(excel_b64)
    excel_bytes = format_excel_bytes(excel_bytes_raw)

    df = normalizar_df(excel_bytes_to_df(excel_bytes))
    arquivo_foco = str(resp.get("arquivo", fname))

    row = pick_row_by_file(df, arquivo_foco)
    if row is None:
        row = df.iloc[-1] if not df.empty else None

    if row is None:
        st.error("❌ Não foi possível localizar a linha do resultado.")
        st.dataframe(df, use_container_width=True)
        return

    total_sec = time.time() - t0_total

    payload = {
        "kind": "wav",
        "filename": arquivo_foco,
        "excel_bytes": excel_bytes,
        "df": df,
        "row": row,
        "timings": {
            "audio_sec": float(audio_sec or 0),
            "transcribe_sec": float(transcribe_sec or 0),
            "eval_sec": float(eval_sec or 0),
            "total_sec": float(total_sec or 0),
        },
        "text_labeled": text_labeled,
        "transcribe_json": json.dumps(data_t, ensure_ascii=False, indent=2),
        "original_wav_name": wav_file.name,
    }
    set_last_result(payload)
    st.success(f"✅ Avaliação concluída em {human_time(total_sec)}")


# ==============================
# 🔁 Batch (até 10) + DOWNLOAD POR ITEM (mesmo padrão do individual)
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

        try:
            with st.spinner(f"Avaliando {idx}/{len(entradas)} no servidor…"):
                resp = api_analyze_text(txt.strip(), filename=name)
        except RuntimeError as e:
            st.error(f"❌ Falha ao avaliar {name}")
            st.code(str(e))
            return

        if not resp.get("ok") or not resp.get("excel_base64"):
            st.error(f"❌ Falha ao avaliar: {name}")
            st.json(resp)
            return

        excel_bytes_raw = decode_excel_base64_to_bytes(resp["excel_base64"])
        excel_bytes = format_excel_bytes(excel_bytes_raw)
        df = normalizar_df(excel_bytes_to_df(excel_bytes))

        arquivo_foco = str(resp.get("arquivo", name))
        row = pick_row_by_file(df, arquivo_foco)
        if row is None:
            row = df.iloc[-1] if not df.empty else None

        if row is None:
            st.error(f"❌ Não consegui localizar linha do resultado: {name}")
            continue

        itens.append(
            {
                "kind": "txt",
                "filename": arquivo_foco,
                "excel_bytes": excel_bytes,
                "df": df,
                "row": row,
                "timings": {},
                "text_labeled": None,
                "transcribe_json": None,
                "original_wav_name": None,
            }
        )

    if not itens:
        st.warning("Nenhum resultado retornou linhas válidas.")
        return

    set_batch_results(itens)

    # tabela resumo (a partir das rows)
    df_final = pd.DataFrame([it["row"] for it in itens if it.get("row") is not None])
    st.success(f"✅ Lote concluído em {human_time(time.time() - started)}")

    st.markdown("---")
    st.markdown("### 📊 Resultados do Lote (TXT)")
    st.dataframe(df_final, use_container_width=True)


def processar_lote_wav(wavs):
    if len(wavs) > 10:
        st.error("Limite: 10 WAVs por lote.")
        return

    itens: List[dict] = []
    started = time.time()

    for idx, wavf in enumerate(wavs, start=1):
        wav_bytes = wavf.getbuffer().tobytes()

        try:
            with st.spinner(f"Transcrevendo {idx}/{len(wavs)}…"):
                data_t = api_transcribe_wav(wav_bytes, filename=wavf.name)
        except RuntimeError as e:
            st.error(f"❌ Falha ao transcrever {wavf.name}")
            st.code(str(e))
            return

        text_labeled = (data_t.get("text_labeled") or "").strip()
        if not text_labeled:
            st.error(f"❌ Transcrição vazia: {wavf.name}")
            st.json(data_t)
            return

        fname = f"{Path(wavf.name).stem}.txt"

        try:
            with st.spinner(f"Avaliando {idx}/{len(wavs)}…"):
                resp = api_analyze_text(text_labeled, filename=fname)
        except RuntimeError as e:
            st.error(f"❌ Falha ao avaliar {wavf.name}")
            st.code(str(e))
            return

        if not resp.get("ok") or not resp.get("excel_base64"):
            st.error(f"❌ Falha ao avaliar: {wavf.name}")
            st.json(resp)
            return

        excel_bytes_raw = decode_excel_base64_to_bytes(resp["excel_base64"])
        excel_bytes = format_excel_bytes(excel_bytes_raw)
        df = normalizar_df(excel_bytes_to_df(excel_bytes))

        arquivo_foco = str(resp.get("arquivo", fname))
        row = pick_row_by_file(df, arquivo_foco)
        if row is None:
            row = df.iloc[-1] if not df.empty else None

        if row is None:
            st.error(f"❌ Não consegui localizar linha do resultado: {wavf.name}")
            continue

        itens.append(
            {
                "kind": "wav",
                "filename": arquivo_foco,
                "excel_bytes": excel_bytes,
                "df": df,
                "row": row,
                "timings": {},
                "text_labeled": text_labeled,
                "transcribe_json": json.dumps(data_t, ensure_ascii=False, indent=2),
                "original_wav_name": wavf.name,
            }
        )

    if not itens:
        st.warning("Nenhum resultado retornou linhas válidas.")
        return

    set_batch_results(itens)

    df_final = pd.DataFrame([it["row"] for it in itens if it.get("row") is not None])
    st.success(f"✅ Lote concluído em {human_time(time.time() - started)}")

    st.markdown("---")
    st.markdown("### 📊 Resultados do Lote (WAV)")
    st.dataframe(df_final, use_container_width=True)


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
# 🧭 Sidebar
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
    st.success("Servidor VPS conectado ✅")
    st.caption(f"Analyze: {_pretty_url(ANALYZE_API_URL)}")
    st.caption(f"Transcribe: {_pretty_url(TRANSCRIBE_API_URL)}")

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
        txt_input = st.text_area(
            "Cole a transcrição aqui",
            height=260,
            value="",
            key="txt_input_single",
        )

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Avaliar texto", use_container_width=True, key="btn_eval_txt_single"):
                ok, msg = validar_transcricao(txt_input)
                if not ok:
                    st.error(msg)
                else:
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
            if st.button("✅ Avaliar áudio", use_container_width=True, key="btn_eval_wav_single"):
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
    st.info("Em lote, o painel mostra os resultados na tela e agora também permite downloads por item ✅")

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

        if st.button("✅ Rodar lote (TXT)", use_container_width=True, key="btn_run_batch_txt"):
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

        if st.button("✅ Rodar lote (WAV)", use_container_width=True, key="btn_run_batch_wav"):
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
if lr and lr.get("row") is not None:
    st.markdown("---")
    st.markdown("## ✅ Resultado atual (individual)")

    filename = str(lr.get("filename") or f"avaliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    base = Path(filename).stem

    row = lr["row"]
    df = lr.get("df")
    excel_bytes = lr.get("excel_bytes")
    timings = lr.get("timings", {}) or {}

    render_header_score_only(filename, row, timings=timings)

    st.markdown("### 📥 Downloads")

    if excel_bytes:
        st.download_button(
            "📥 Baixar Excel (avaliação)",
            data=excel_bytes,
            file_name=f"{base}_avaliacao_spin.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_excel_single_{base}",
        )

    if lr.get("kind") == "wav":
        if lr.get("text_labeled"):
            st.download_button(
                "📥 Baixar TXT (rotulado)",
                data=lr["text_labeled"],
                file_name=f"{base}_transcricao_rotulada.txt",
                use_container_width=True,
                key=f"dl_txt_single_{base}",
            )
        if lr.get("transcribe_json"):
            st.download_button(
                "📥 Baixar JSON (transcrição)",
                data=lr["transcribe_json"],
                file_name=f"{base}_transcricao.json",
                use_container_width=True,
                key=f"dl_json_single_{base}",
            )

    if isinstance(df, pd.DataFrame) and not df.empty:
        with st.expander("📊 Ver tabela completa (Excel em DataFrame)", expanded=False):
            st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧾 Detalhamento por fase")
    render_avaliacao_completa(row)


# ==============================
# ✅ Resultados do LOTE + downloads por item
# ==============================
br = st.session_state.get("batch_results")
if br:
    st.markdown("---")
    st.markdown("## ✅ Resultados (lote) — Downloads por item")

    for i, item in enumerate(br, start=1):
        row = item.get("row")
        if row is None:
            continue

        filename = str(item.get("filename") or f"item_{i}.txt")
        base = Path(filename).stem

        with st.expander(f"📌 {i}. {filename}", expanded=False):
            # header score
            render_header_score_only(filename, row, timings=item.get("timings"))

            st.markdown("### 📥 Downloads do item")

            excel_bytes = item.get("excel_bytes")
            if excel_bytes:
                st.download_button(
                    "📥 Baixar Excel (avaliação)",
                    data=excel_bytes,
                    file_name=f"{base}_avaliacao_spin.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"dl_batch_excel_{i}_{base}",
                )

            if item.get("kind") == "wav":
                if item.get("text_labeled"):
                    st.download_button(
                        "📥 Baixar TXT (rotulado)",
                        data=item["text_labeled"],
                        file_name=f"{base}_transcricao_rotulada.txt",
                        use_container_width=True,
                        key=f"dl_batch_txt_{i}_{base}",
                    )
                if item.get("transcribe_json"):
                    st.download_button(
                        "📥 Baixar JSON (transcrição)",
                        data=item["transcribe_json"],
                        file_name=f"{base}_transcricao.json",
                        use_container_width=True,
                        key=f"dl_batch_json_{i}_{base}",
                    )

            df = item.get("df")
            if isinstance(df, pd.DataFrame) and not df.empty:
                with st.expander("📊 Ver tabela completa (DataFrame)", expanded=False):
                    st.dataframe(df, use_container_width=True)

            st.markdown("---")
            st.markdown("### 🧾 Detalhamento por fase")
            render_avaliacao_completa(row)


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
