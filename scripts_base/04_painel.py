# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT + WAV)
# MODO ÚNICO: VPS OBRIGATÓRIO (Streamlit / Cloud)
# ✅ Parte 1/2:
#    - Resultado persiste no download (sem reset)
#    - Remove exemplo do TXT
#    - Pontuação em destaque (sem nome do arquivo no topo)
#    - Tempos (transcrição/avaliação) e comparação com duração do áudio
#    - Download com nome de arquivo correto
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
from typing import Optional, Tuple, List

import streamlit as st
import pandas as pd
import requests


# ==============================
# ⚙️ Configurações obrigatórias
# ==============================
ANALYZE_API_URL = os.getenv("ANALYZE_API_URL", "").strip()
TRANSCRIBE_API_URL = os.getenv("TRANSCRIBE_API_URL", "").strip()
API_TIMEOUT_S = int(os.getenv("API_TIMEOUT_S", "7200"))

if not ANALYZE_API_URL:
    st.error("❌ ANALYZE_API_URL não configurado.")
    st.stop()

if not TRANSCRIBE_API_URL:
    st.error("❌ TRANSCRIBE_API_URL não configurado.")
    st.stop()


# ==============================
# 📄 Página
# ==============================
st.set_page_config(
    page_title="SPIN Analyzer — Avaliação de Ligações",
    page_icon="🎧",
    layout="wide",
)


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
h1, h2, h3 {
  color: #0B63F3;
}
.card{
  background: #FFFFFF !important;
  color: #0B1220 !important;
  border: 1px solid #C7D6F5 !important;
  border-radius: 18px;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: 0 8px 24px rgba(11,18,32,0.08);
}

/* força texto escuro dentro do card (resolve letra branca) */
.card *{
  color: #0B1220 !important;
}

/* badges */
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
</style>
""",
    unsafe_allow_html=True,
)


# ==============================
# 📂 Diretórios temporários
# ==============================
BASE_DIR = Path(__file__).resolve().parent
TMP_DIR = BASE_DIR / "_tmp_painel"
TMP_DIR.mkdir(exist_ok=True)

TMP_TXT = TMP_DIR / "txt"
TMP_WAV = TMP_DIR / "wav"
TMP_TXT.mkdir(exist_ok=True)
TMP_WAV.mkdir(exist_ok=True)


# ==============================
# 🔒 Helpers de limpeza
# ==============================
def limpar_temporarios():
    try:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        TMP_DIR.mkdir(exist_ok=True)
        TMP_TXT.mkdir(exist_ok=True)
        TMP_WAV.mkdir(exist_ok=True)
    except Exception:
        pass


# ==============================
# 🌐 API — VPS
# ==============================
def api_analyze_text(text: str, filename: str) -> dict:
    payload = {
        "text": text,
        "filename": filename,
    }
    r = requests.post(
        ANALYZE_API_URL,
        json=payload,
        timeout=API_TIMEOUT_S,
    )
    r.raise_for_status()
    return r.json()


def api_transcribe_wav(wav_bytes: bytes, filename: str) -> dict:
    files = {
        "file": (filename, wav_bytes, "audio/wav")
    }
    r = requests.post(
        TRANSCRIBE_API_URL,
        files=files,
        timeout=API_TIMEOUT_S,
    )
    r.raise_for_status()
    return r.json()


# ==============================
# ✅ Validação do TXT
# ==============================
def validar_transcricao(txt: str) -> Tuple[bool, str]:
    linhas = [l.strip() for l in txt.splitlines() if l.strip()]
    if len(linhas) < 4:
        return False, "Texto muito curto."
    if not any(re.match(r"^\[(VENDEDOR|CLIENTE)\]", l, re.I) for l in linhas):
        return False, "Formato inválido. Use [VENDEDOR] e [CLIENTE]."
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
    return f"{int(sec//60)}m {int(sec%60)}s"


# ==============================
# 🧠 Estado: persistir último resultado (evita reset no download)
# ==============================
if "view" not in st.session_state:
    st.session_state["view"] = "single"

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None


def set_last_result(**kwargs):
    st.session_state["last_result"] = kwargs


def clear_last_result():
    st.session_state["last_result"] = None


# ==============================
# 🧭 Navegação
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")
    if st.button("👤 Avaliação Individual"):
        st.session_state["view"] = "single"
    if st.button("📊 Visão Gerencial"):
        st.session_state["view"] = "batch"

    st.markdown("---")
    st.success("Servidor VPS conectado ✅")

    st.markdown("---")
    if st.session_state.get("last_result"):
        if st.button("🧹 Limpar resultado atual", use_container_width=True):
            clear_last_result()
            st.rerun()


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
# 📦 Helpers: Excel do retorno
# ==============================
def decode_excel_base64_to_bytes(excel_b64: str) -> bytes:
    return base64.b64decode(excel_b64.encode("utf-8"))


def excel_bytes_to_df(excel_bytes: bytes) -> pd.DataFrame:
    import io
    bio = io.BytesIO(excel_bytes)
    df = pd.read_excel(bio)
    return df


def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "arquivo" not in df.columns:
        df["arquivo"] = ""

    # padroniza nomes usados no painel
    df.rename(
        columns={
            "implicacao_feedback": "implication_feedback",
            "necessidade_feedback": "need_payoff_feedback",
        },
        inplace=True,
    )

    # garante colunas numéricas
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
# 🧩 Scoring + UI
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
            "com ausência de enquadramento claro e pouco ou nenhum diagnóstico estruturado. "
            "Não há evidências consistentes de exploração de situação, problema, impacto ou valor."
        )
    if score25 <= 12:
        return (
            "A avaliação revela sinais iniciais de estrutura consultiva, porém com execução instável. "
            "Algumas etapas do método SPIN aparecem de forma pontual, mas sem profundidade ou encadeamento lógico."
        )
    if score25 <= 18:
        return (
            "A conversa apresenta uma boa base de execução do método SPIN. "
            "Há direcionamento e início de diagnóstico consultivo, com oportunidades claras de evolução."
        )
    if score25 <= 23:
        return (
            "A avaliação indica uma execução forte e consistente do método SPIN, "
            "com bom encadeamento de diagnóstico e exploração adequada de impacto."
        )
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


# ==============================
# ✅ Execuções: salvam resultado em session_state (sem sumir no download)
# ==============================
def processar_txt_unico(txt: str, fname: str):
    started = time.time()

    with st.spinner("Avaliando no servidor (VPS)…"):
        resp = api_analyze_text(txt.strip(), filename=fname)

    if not resp.get("ok"):
        st.error("❌ O servidor não conseguiu avaliar este texto.")
        st.json(resp)
        return

    excel_b64 = resp.get("excel_base64")
    if not excel_b64:
        st.error("❌ O servidor respondeu ok, mas não retornou excel_base64.")
        st.json(resp)
        return

    excel_bytes = decode_excel_base64_to_bytes(excel_b64)
    elapsed_eval = time.time() - started

    df = normalizar_df(excel_bytes_to_df(excel_bytes))
    arquivo_foco = str(resp.get("arquivo", fname))

    if "arquivo" in df.columns and (df["arquivo"].astype(str) == arquivo_foco).any():
        row = pick_row_by_file(df, arquivo_foco)
    else:
        row = df.iloc[-1] if not df.empty else None

    set_last_result(
        kind="txt",
        filename=arquivo_foco,
        excel_bytes=excel_bytes,
        df=df,
        row=row,
        t_audio_sec=None,
        t_transcribe_sec=None,
        t_eval_sec=elapsed_eval,
        text_labeled=None,
        transcribe_json=None,
        original_wav_name=None,
    )

    st.success(f"✅ Avaliação concluída em {human_time(elapsed_eval)}")


def processar_wav_unico(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()

    tmp_wav = TMP_WAV / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    tmp_wav.write_bytes(wav_bytes)

    try:
        dur = duracao_wav_seg(tmp_wav)
    except Exception:
        dur = 0.0

    if dur > 600:
        st.error(f"❌ Áudio tem {dur/60:.1f} minutos. Limite recomendado: 10 minutos.")
        return

    t0 = time.time()
    with st.spinner("Transcrevendo no servidor (VPS)…"):
        data_t = api_transcribe_wav(wav_bytes, filename=wav_file.name)
    t_transcribe = time.time() - t0

    text_labeled = (data_t.get("text_labeled") or "").strip()
    if not text_labeled:
        st.error("❌ A transcrição veio vazia.")
        st.json(data_t)
        return

    st.success("✅ Transcrição concluída")

    fname = f"painel_wav_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    t1 = time.time()
    with st.spinner("Avaliando no servidor (VPS)…"):
        resp = api_analyze_text(text_labeled, filename=fname)
    t_eval = time.time() - t1

    if not resp.get("ok"):
        st.error("❌ O servidor não conseguiu avaliar este áudio.")
        st.json(resp)
        return

    excel_b64 = resp.get("excel_base64")
    if not excel_b64:
        st.error("❌ O servidor respondeu ok, mas não retornou excel_base64.")
        st.json(resp)
        return

    excel_bytes = decode_excel_base64_to_bytes(excel_b64)
    df = normalizar_df(excel_bytes_to_df(excel_bytes))

    arquivo_foco = str(resp.get("arquivo", fname))
    row = pick_row_by_file(df, arquivo_foco)
    if row is None:
        row = df.iloc[-1] if not df.empty else None

    set_last_result(
        kind="wav",
        filename=arquivo_foco,
        excel_bytes=excel_bytes,
        df=df,
        row=row,
        t_audio_sec=dur,
        t_transcribe_sec=t_transcribe,
        t_eval_sec=t_eval,
        text_labeled=text_labeled,
        transcribe_json=json.dumps(data_t, ensure_ascii=False, indent=2),
        original_wav_name=wav_file.name,
    )

    st.success(f"✅ Avaliação concluída em {human_time(t_transcribe + t_eval)}")


# ==============================
# ✅ UI: Telas
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")
    tab_txt, tab_wav = st.tabs(["📝 Colar transcrição (TXT)", "🎧 Enviar áudio (WAV)"])

    with tab_txt:
        txt_input = st.text_area("Cole a transcrição aqui", height=260, value="", key="txt_input_single")
        if st.button("✅ Avaliar texto", use_container_width=True):
            ok, msg = validar_transcricao(txt_input)
            if not ok:
                st.error(msg)
            else:
                limpar_temporarios()
                clear_last_result()
                fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                processar_txt_unico(txt_input, fname)

    with tab_wav:
        up_wav = st.file_uploader("Envie um WAV (até ~10 min)", type=["wav"])
        if st.button("✅ Avaliar áudio", use_container_width=True):
            if up_wav is None:
                st.error("Envie um WAV para continuar.")
            else:
                limpar_temporarios()
                clear_last_result()
                processar_wav_unico(up_wav)

else:
    st.markdown("### 📊 Visão Gerencial (até 10)")
    st.info("Em lote, o painel mostra os resultados na tela, mas não persiste downloads por item. (vamos refinar isso na Parte 2/2)")
    # mantemos lote como estava (será refinado depois)

    modo = st.selectbox("Tipo de entrada", ["TXT (arquivos .txt ou colar vários)", "WAV (áudios .wav)"], index=0)
    st.markdown("---")

    if modo.startswith("TXT"):
        up_txts = st.file_uploader("Envie até 10 arquivos .txt", type=["txt"], accept_multiple_files=True)
        st.markdown("Ou cole vários blocos separados por uma linha contendo `---`")
        multi_txt = st.text_area("Cole aqui (separe com ---)", height=220, value="", key="txt_input_batch")

        def processar_lote_txt(entradas: List[Tuple[str, str]]):
            if len(entradas) > 10:
                st.error("Limite: 10 entradas por lote.")
                return

            resultados = []
            started = time.time()

            for idx, (name, txt) in enumerate(entradas, start=1):
                ok, msg = validar_transcricao(txt)
                if not ok:
                    st.error(f"❌ {name}: {msg}")
                    return

                with st.spinner(f"Avaliando {idx}/{len(entradas)} no servidor…"):
                    resp = api_analyze_text(txt.strip(), filename=name)

                if not resp.get("ok") or not resp.get("excel_base64"):
                    st.error(f"❌ Falha ao avaliar: {name}")
                    st.json(resp)
                    return

                excel_bytes = decode_excel_base64_to_bytes(resp["excel_base64"])
                df = normalizar_df(excel_bytes_to_df(excel_bytes))
                row = df.iloc[-1] if not df.empty else None
                if row is not None:
                    resultados.append(row)

            if not resultados:
                st.warning("Nenhum resultado retornou linhas válidas.")
                return

            df_final = pd.DataFrame(resultados)
            st.success(f"✅ Lote concluído em {human_time(time.time()-started)}")
            st.markdown("---")
            st.markdown("### 📊 Resultados do Lote")
            st.dataframe(df_final, use_container_width=True)
            st.markdown("---")
            st.markdown("### 🧾 Avaliação completa por ligação")
            for _, row in df_final.iterrows():
                render_avaliacao_completa(row)

        if st.button("✅ Rodar lote (TXT)", use_container_width=True):
            entradas = []
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
                processar_lote_txt(entradas)

    else:
        up_wavs = st.file_uploader("Envie até 10 WAVs", type=["wav"], accept_multiple_files=True)

        def processar_lote_wav(wavs):
            if len(wavs) > 10:
                st.error("Limite: 10 WAVs por lote.")
                return

            resultados = []
            started = time.time()

            for idx, wavf in enumerate(wavs, start=1):
                wav_bytes = wavf.getbuffer().tobytes()

                with st.spinner(f"Transcrevendo {idx}/{len(wavs)}…"):
                    data_t = api_transcribe_wav(wav_bytes, filename=wavf.name)

                text_labeled = (data_t.get("text_labeled") or "").strip()
                if not text_labeled:
                    st.error(f"❌ Transcrição vazia: {wavf.name}")
                    st.json(data_t)
                    return

                fname = f"batchwav_{idx:02d}_{Path(wavf.name).stem}.txt"

                with st.spinner(f"Avaliando {idx}/{len(wavs)}…"):
                    resp = api_analyze_text(text_labeled, filename=fname)

                if not resp.get("ok") or not resp.get("excel_base64"):
                    st.error(f"❌ Falha ao avaliar: {wavf.name}")
                    st.json(resp)
                    return

                excel_bytes = decode_excel_base64_to_bytes(resp["excel_base64"])
                df = normalizar_df(excel_bytes_to_df(excel_bytes))
                row = df.iloc[-1] if not df.empty else None
                if row is not None:
                    resultados.append(row)

            if not resultados:
                st.warning("Nenhum resultado retornou linhas válidas.")
                return

            df_final = pd.DataFrame(resultados)
            st.success(f"✅ Lote WAV concluído em {human_time(time.time()-started)}")
            st.markdown("---")
            st.markdown("### 📊 Resultados do Lote (WAV)")
            st.dataframe(df_final, use_container_width=True)
            st.markdown("---")
            st.markdown("### 🧾 Avaliação completa por ligação")
            for _, row in df_final.iterrows():
                render_avaliacao_completa(row)

        if st.button("✅ Rodar lote (WAV)", use_container_width=True):
            if not up_wavs:
                st.error("Envie pelo menos 1 WAV.")
            else:
                limpar_temporarios()
                processar_lote_wav(up_wavs)


# ==============================
# ✅ Render persistente + Downloads (não somem ao baixar)
# ==============================
lr = st.session_state.get("last_result")

if lr and lr.get("row") is not None:
    st.markdown("---")
    st.markdown("## ✅ Resultado detalhado")

    row = lr["row"]
    phase_scores = build_phase_scores_from_row(row)
    score25 = score_total_25(phase_scores)
    qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)

    # Pontuação em destaque (sem nome de arquivo)
    st.markdown(
        f"""
<div class="card">
  <h2 style="margin:0; font-size:2rem;">Pontuação: {score25}/25</h2>
  <p style="margin-top:6px;margin-bottom:0;">
    <span class="badge {qualidade_tag}">{qualidade_label}</span>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # Tempos e comparação com duração do áudio
    kind = lr.get("kind")
    if kind == "wav":
        dur = float(lr.get("t_audio_sec") or 0)
        tt = float(lr.get("t_transcribe_sec") or 0)
        te = float(lr.get("t_eval_sec") or 0)
        total = tt + te

        ratio_txt = ""
        if dur > 0:
            ratio = total / dur
            if ratio <= 1:
                ratio_txt = f"<br/><b>Comparação:</b> pipeline ~{ratio:.2f}x do tempo da ligação (mais rápido)"
            else:
                ratio_txt = f"<br/><b>Comparação:</b> pipeline ~{ratio:.2f}x do tempo da ligação (mais lento)"

        st.markdown(
            f"""
<div class="card">
  <h3 style="margin:0;">⏱️ Tempos</h3>
  <p style="margin-top:6px;margin-bottom:0;">
    <b>Duração do áudio:</b> {human_time(dur)}<br/>
    <b>Transcrição:</b> {human_time(tt)}<br/>
    <b>Avaliação:</b> {human_time(te)}<br/>
    <b>Total pipeline:</b> {human_time(total)}
    {ratio_txt}
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        te = float(lr.get("t_eval_sec") or 0)
        st.markdown(
            f"""
<div class="card">
  <h3 style="margin:0;">⏱️ Tempo</h3>
  <p style="margin-top:6px;margin-bottom:0;">
    <b>Avaliação:</b> {human_time(te)}
  </p>
</div>
""",
            unsafe_allow_html=True,
        )

    # Downloads com nome correto do arquivo
    st.markdown("### 📥 Downloads")

    filename = str(lr.get("filename") or f"avaliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    base = Path(filename).stem

    excel_name = f"{base}_avaliacao.xlsx"
    st.download_button(
        "📥 Baixar Excel (avaliação)",
        data=lr["excel_bytes"],
        file_name=excel_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key=f"dl_excel_{base}",
    )

    # WAV: também baixar TXT e JSON, sem reset
    if lr.get("kind") == "wav":
        if lr.get("text_labeled"):
            st.download_button(
                "📥 Baixar TXT (rotulado)",
                data=lr["text_labeled"],
                file_name=f"{base}_transcricao_rotulada.txt",
                use_container_width=True,
                key=f"dl_txt_{base}",
            )
        if lr.get("transcribe_json"):
            st.download_button(
                "📥 Baixar JSON (transcrição)",
                data=lr["transcribe_json"],
                file_name=f"{base}_transcricao.json",
                use_container_width=True,
                key=f"dl_json_{base}",
            )

    st.markdown("---")
    st.markdown("### 📊 Dados (Excel)")
    df = lr.get("df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    render_avaliacao_completa(row)


st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3A4A63;'>"
    "SPIN Analyzer — Projeto Tele_IA 2026 | Desenvolvido por Paulo Coutinho"
    "</div>",
    unsafe_allow_html=True,
)

# ==============================
# 📏 Excel: formatar largura + wrap text (não corta textos)
# ==============================
from io import BytesIO

EXCEL_WRAP_TEXT = os.getenv("EXCEL_WRAP_TEXT", "1").strip() not in ("0", "false", "False", "")
EXCEL_DEFAULT_COL_W = int(os.getenv("EXCEL_DEFAULT_COL_W", "22"))
EXCEL_TEXT_COL_W = int(os.getenv("EXCEL_TEXT_COL_W", "55"))
EXCEL_MAX_COL_W = int(os.getenv("EXCEL_MAX_COL_W", "80"))

def format_excel_bytes(excel_bytes: bytes) -> bytes:
    """
    Formata o Excel retornado pela API para NÃO 'cortar' textos na visualização:
    - Ajusta largura de colunas (texto e padrão)
    - Aplica wrap_text e alinhamento topo/esquerda em colunas textuais
    - Congela cabeçalho
    Roda no painel (não depende do VPS).
    """
    if not excel_bytes:
        return excel_bytes

    try:
        from openpyxl import load_workbook
        from openpyxl.styles import Alignment
    except Exception:
        # Se openpyxl não estiver disponível no Streamlit Cloud, retorna original
        return excel_bytes

    bio = BytesIO(excel_bytes)
    wb = load_workbook(bio)
    ws = wb.active

    # Congela header
    ws.freeze_panes = "A2"

    long_text_markers = (
        "_texto", "_feedback", "justific", "trecho", "observ", "coment", "resumo"
    )

    # Mapa header -> col index
    headers = {}
    for col_idx in range(1, ws.max_column + 1):
        v = ws.cell(row=1, column=col_idx).value
        if v is None:
            continue
        headers[str(v)] = col_idx

    wrap_align = Alignment(wrap_text=True, vertical="top", horizontal="left")
    normal_align = Alignment(wrap_text=False, vertical="top", horizontal="left")

    # Proteção: custo/tempo (mas suficiente pro uso real)
    max_rows = min(ws.max_row, 5000)

    for header, col_idx in headers.items():
        h = str(header).lower()
        is_long = any(m in h for m in long_text_markers)

        col_letter = ws.cell(row=1, column=col_idx).column_letter
        if is_long:
            ws.column_dimensions[col_letter].width = min(EXCEL_TEXT_COL_W, EXCEL_MAX_COL_W)
        else:
            ws.column_dimensions[col_letter].width = min(EXCEL_DEFAULT_COL_W, EXCEL_MAX_COL_W)

        if EXCEL_WRAP_TEXT:
            for r in range(1, max_rows + 1):
                cell = ws.cell(row=r, column=col_idx)
                cell.alignment = wrap_align if is_long else normal_align

    ws.row_dimensions[1].height = 22

    out = BytesIO()
    wb.save(out)
    return out.getvalue()


# ==============================
# 🧠 Sessão: manter resultado sem reset ao baixar
# ==============================
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None  # dict: {filename, df, row, excel_bytes, timings}
if "last_run_id" not in st.session_state:
    st.session_state["last_run_id"] = None


def _set_last_result(filename: str, df: pd.DataFrame, row: pd.Series, excel_bytes: bytes, timings: dict):
    st.session_state["last_result"] = {
        "filename": filename,
        "df": df,
        "row": row,
        "excel_bytes": excel_bytes,
        "timings": timings or {},
    }
    st.session_state["last_run_id"] = datetime.now().isoformat(timespec="seconds")


def _clear_last_result():
    st.session_state["last_result"] = None
    st.session_state["last_run_id"] = None


# ==============================
# 🧾 UI: bloco de resultado em destaque (pontuação grande)
# ==============================
def render_header_score_only(filename: str, row: pd.Series, timings: dict | None = None):
    phase_scores = build_phase_scores_from_row(row)
    score25 = score_total_25(phase_scores)
    qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)

    # Mostra pontuação em destaque e esconde nome do arquivo na UI (pedido do cliente)
    # Mas o arquivo baixado mantém nome correto.
    st.markdown(
        f"""
<div class="card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:14px;">
    <div>
      <div class="badge {qualidade_tag}" style="margin-bottom:8px;">{qualidade_label}</div>
      <div style="font-size:44px;font-weight:900;line-height:1;margin:0;color:#0B1220;">
        {score25}<span style="font-size:22px;font-weight:800;">/25</span>
      </div>
      <div style="margin-top:8px;color:#3A4A63;font-weight:700;">
        Pontuação SPIN (Abertura + Situação + Problema + Implicação + Need-payoff)
      </div>
    </div>
    <div style="text-align:right;">
      <div style="color:#3A4A63;font-weight:800;margin-bottom:6px;">Identificador</div>
      <div class="badge" title="{filename}">{filename}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if timings:
        # timings esperados: audio_sec, transcribe_sec, eval_sec, total_sec
        audio_sec = float(timings.get("audio_sec", 0) or 0)
        transcribe_sec = float(timings.get("transcribe_sec", 0) or 0)
        eval_sec = float(timings.get("eval_sec", 0) or 0)
        total_sec = float(timings.get("total_sec", 0) or 0)

        def _ratio_str(x, base):
            if base <= 0:
                return "—"
            return f"{(x/base):.2f}x"

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


# ==============================
# 🔁 Execução: TXT (1 item) — mantém resultado
# ==============================
def processar_txt_unico(txt: str, fname: str):
    started = time.time()

    with st.spinner("Avaliando no servidor (VPS)…"):
        resp = api_analyze_text(txt.strip(), filename=fname)

    if not resp.get("ok"):
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
    if "arquivo" in df.columns and (df["arquivo"].astype(str) == arquivo_foco).any():
        row = pick_row_by_file(df, arquivo_foco)
    else:
        row = df.iloc[-1] if not df.empty else None

    if row is None:
        st.error("❌ Não foi possível localizar a linha do resultado.")
        st.dataframe(df, use_container_width=True)
        return

    timings = {
        "audio_sec": 0,
        "transcribe_sec": 0,
        "eval_sec": elapsed_eval,
        "total_sec": elapsed_eval,
    }

    _set_last_result(arquivo_foco, df, row, excel_bytes, timings)


# ==============================
# 🔁 Execução: WAV (1 item) — mantém resultado
# ==============================
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

    t0_trans = time.time()
    with st.spinner("Transcrevendo no servidor (VPS)…"):
        data_t = api_transcribe_wav(wav_bytes, filename=wav_file.name)
    transcribe_sec = time.time() - t0_trans

    text_labeled = (data_t.get("text_labeled") or "").strip()
    if not text_labeled:
        st.error("❌ A transcrição veio vazia.")
        st.json(data_t)
        return

    # downloads: NÃO resetam o app
    st.success("✅ Transcrição concluída")
    st.download_button(
        "📥 Baixar TXT (rotulado)",
        data=text_labeled,
        file_name=f"{Path(wav_file.name).stem}_transcricao_rotulada.txt",
        use_container_width=True
    )
    st.download_button(
        "📥 Baixar JSON (transcrição)",
        data=json.dumps(data_t, ensure_ascii=False, indent=2),
        file_name=f"{Path(wav_file.name).stem}_transcricao.json",
        use_container_width=True
    )

    # Avaliação
    fname = f"{Path(wav_file.name).stem}.txt"
    t0_eval = time.time()
    with st.spinner("Avaliando no servidor (VPS)…"):
        resp = api_analyze_text(text_labeled, filename=fname)
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
    timings = {
        "audio_sec": float(audio_sec or 0),
        "transcribe_sec": float(transcribe_sec or 0),
        "eval_sec": float(eval_sec or 0),
        "total_sec": float(total_sec or 0),
    }

    _set_last_result(arquivo_foco, df, row, excel_bytes, timings)


# ==============================
# 🔁 Execução: Lote TXT (até 10) — mantém tabela e detalha
# ==============================
def processar_lote_txt(entradas: list[tuple[str, str]]):
    if len(entradas) > 10:
        st.error("Limite: 10 entradas por lote.")
        return

    resultados = []
    started = time.time()

    for idx, (name, txt) in enumerate(entradas, start=1):
        ok, msg = validar_transcricao(txt)
        if not ok:
            st.error(f"❌ {name}: {msg}")
            return

        with st.spinner(f"Avaliando {idx}/{len(entradas)} no servidor…"):
            resp = api_analyze_text(txt.strip(), filename=name)

        if not resp.get("ok") or not resp.get("excel_base64"):
            st.error(f"❌ Falha ao avaliar: {name}")
            st.json(resp)
            return

        excel_bytes_raw = decode_excel_base64_to_bytes(resp["excel_base64"])
        excel_bytes = format_excel_bytes(excel_bytes_raw)
        df = normalizar_df(excel_bytes_to_df(excel_bytes))

        row = df[df["arquivo"].astype(str) == str(resp.get("arquivo", name))].iloc[-1] if not df.empty else None
        if row is not None:
            resultados.append(row)

    if not resultados:
        st.warning("Nenhum resultado retornou linhas válidas.")
        return

    df_final = pd.DataFrame(resultados)
    st.success(f"✅ Lote concluído em {human_time(time.time()-started)}")

    st.markdown("---")
    st.markdown("### 📊 Resultados do Lote")
    st.dataframe(df_final, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧾 Avaliação completa por ligação")
    for _, row in df_final.iterrows():
        fname = str(row.get("arquivo", "—"))
        render_avaliacao_completa(fname, row)


# ==============================
# 🔁 Execução: Lote WAV (até 10) — mantém tabela e detalha
# ==============================
def processar_lote_wav(wavs):
    if len(wavs) > 10:
        st.error("Limite: 10 WAVs por lote.")
        return

    resultados = []
    started = time.time()

    for idx, wavf in enumerate(wavs, start=1):
        wav_bytes = wavf.getbuffer().tobytes()

        with st.spinner(f"Transcrevendo {idx}/{len(wavs)}…"):
            data_t = api_transcribe_wav(wav_bytes, filename=wavf.name)

        text_labeled = (data_t.get("text_labeled") or "").strip()
        if not text_labeled:
            st.error(f"❌ Transcrição vazia: {wavf.name}")
            st.json(data_t)
            return

        fname = f"{Path(wavf.name).stem}.txt"

        with st.spinner(f"Avaliando {idx}/{len(wavs)}…"):
            resp = api_analyze_text(text_labeled, filename=fname)

        if not resp.get("ok") or not resp.get("excel_base64"):
            st.error(f"❌ Falha ao avaliar: {wavf.name}")
            st.json(resp)
            return

        excel_bytes_raw = decode_excel_base64_to_bytes(resp["excel_base64"])
        excel_bytes = format_excel_bytes(excel_bytes_raw)
        df = normalizar_df(excel_bytes_to_df(excel_bytes))

        row = df[df["arquivo"].astype(str) == str(resp.get("arquivo", fname))].iloc[-1] if not df.empty else None
        if row is not None:
            resultados.append(row)

    if not resultados:
        st.warning("Nenhum resultado retornou linhas válidas.")
        return

    df_final = pd.DataFrame(resultados)
    st.success(f"✅ Lote WAV concluído em {human_time(time.time()-started)}")

    st.markdown("---")
    st.markdown("### 📊 Resultados do Lote (WAV)")
    st.dataframe(df_final, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧾 Avaliação completa por ligação")
    for _, row in df_final.iterrows():
        fname = str(row.get("arquivo", "—"))
        render_avaliacao_completa(fname, row)


# ==============================
# ✅ UI: Telas (com resultado persistente)
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")
    tab_txt, tab_wav = st.tabs(["📝 Colar transcrição (TXT)", "🎧 Enviar áudio (WAV)"])

    with tab_txt:
        # ✅ Pedido do cliente: remover exemplo (deixa vazio)
        txt_input = st.text_area("Cole a transcrição aqui", height=260, value="")

        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Avaliar texto", use_container_width=True):
                ok, msg = validar_transcricao(txt_input)
                if not ok:
                    st.error(msg)
                else:
                    limpar_temporarios()
                    # ✅ nome do arquivo baixado precisa ter nome real (identificador)
                    fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    processar_txt_unico(txt_input, fname)

        with colB:
            if st.button("🧹 Limpar resultado atual", use_container_width=True):
                _clear_last_result()

    with tab_wav:
        up_wav = st.file_uploader("Envie um WAV (até ~10 min)", type=["wav"])
        colA, colB = st.columns(2)
        with colA:
            if st.button("✅ Avaliar áudio", use_container_width=True):
                if up_wav is None:
                    st.error("Envie um WAV para continuar.")
                else:
                    limpar_temporarios()
                    processar_wav_unico(up_wav)
        with colB:
            if st.button("🧹 Limpar resultado atual", use_container_width=True, key="clear_wav"):
                _clear_last_result()

else:
    st.markdown("### 📊 Visão Gerencial (até 10)")
    modo = st.selectbox("Tipo de entrada", ["TXT (arquivos .txt ou colar vários)", "WAV (áudios .wav)"], index=0)
    st.markdown("---")

    if modo.startswith("TXT"):
        up_txts = st.file_uploader("Envie até 10 arquivos .txt", type=["txt"], accept_multiple_files=True)
        st.markdown("Ou cole vários blocos separados por uma linha contendo `---`")
        multi_txt = st.text_area("Cole aqui (separe com ---)", height=220, value="")

        if st.button("✅ Rodar lote (TXT)", use_container_width=True):
            entradas = []

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
                processar_lote_txt(entradas)

    else:
        up_wavs = st.file_uploader("Envie até 10 WAVs", type=["wav"], accept_multiple_files=True)

        if st.button("✅ Rodar lote (WAV)", use_container_width=True):
            if not up_wavs:
                st.error("Envie pelo menos 1 WAV.")
            else:
                limpar_temporarios()
                processar_lote_wav(up_wavs)


# ==============================
# ✅ Resultado persistente (não some ao baixar)
# ==============================
last = st.session_state.get("last_result")
if last:
    st.markdown("---")
    st.markdown("## ✅ Resultado atual")

    filename = last["filename"]
    df = last["df"]
    row = last["row"]
    excel_bytes = last["excel_bytes"]
    timings = last.get("timings", {}) or {}

    # Pontuação em destaque (pedido do cliente)
    render_header_score_only(filename, row, timings=timings)

    # Download do Excel: ✅ nome com identificador real
    st.download_button(
        "📥 Baixar Excel (avaliação)",
        data=excel_bytes,
        file_name=f"{Path(filename).stem}_avaliacao_spin_avancada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    with st.expander("📊 Ver tabela completa (Excel em DataFrame)", expanded=False):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧾 Detalhamento por fase")
    render_avaliacao_completa(filename, row)

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3A4A63;'>"
    "SPIN Analyzer — Projeto Tele_IA 2026 | Desenvolvido por Paulo Coutinho"
    "</div>",
    unsafe_allow_html=True,
)
