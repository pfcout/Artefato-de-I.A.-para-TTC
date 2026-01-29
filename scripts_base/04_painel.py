# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT + WAV)
# MODO ÚNICO: VPS OBRIGATÓRIO (Streamlit / Cloud)
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

import streamlit as st
import pandas as pd
import requests

# ==============================
# ⚙️ Configurações obrigatórias
# ==============================
ANALYZE_API_URL = os.getenv("ANALYZE_API_URL", "").strip()
TRANSCRIBE_API_URL = os.getenv("TRANSCRIBE_API_URL", "").strip()

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
        timeout=7200,
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
        timeout=7200,
    )
    r.raise_for_status()
    return r.json()


# ==============================
# ✅ Validação do TXT
# ==============================
def validar_transcricao(txt: str) -> tuple[bool, str]:
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
    if sec < 60:
        return f"{int(sec)}s"
    return f"{int(sec//60)}m {int(sec%60)}s"


# ==============================
# 🧭 Navegação
# ==============================
if "view" not in st.session_state:
    st.session_state["view"] = "single"


with st.sidebar:
    st.markdown("### 🧭 Navegação")
    if st.button("👤 Avaliação Individual"):
        st.session_state["view"] = "single"
    if st.button("📊 Visão Gerencial"):
        st.session_state["view"] = "batch"

    st.markdown("---")
    st.success("Servidor VPS conectado ✅")


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
    # Lê o excel retornado pelo Analyze API direto da memória
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


def pick_row_by_file(df: pd.DataFrame, filename: str) -> pd.Series | None:
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


def label_qualidade_por_score25(score25: int) -> tuple[str, str]:
    if score25 <= 8:
        return "Baixa", "bad"
    if score25 <= 18:
        return "Moderada", "warn"
    return "Alta", "ok"


def msg_geral_por_score25(score25: int) -> str:
    if score25 <= 6:
        return (
            "A pontuação indica uma execução muito fraca do método SPIN. "
            "A conversa se manteve predominantemente reativa e operacional, "
            "com ausência de enquadramento claro e pouco ou nenhum diagnóstico estruturado. "
            "Não há evidências consistentes de exploração de situação, problema, impacto ou valor, "
            "o que compromete a construção consultiva da conversa e reduz significativamente o potencial de avanço."
        )

    if score25 <= 12:
        return (
            "A avaliação revela sinais iniciais de estrutura consultiva, porém com execução instável. "
            "Algumas etapas do método SPIN aparecem de forma pontual, mas sem profundidade ou encadeamento lógico. "
            "Há pouca consistência nos follow-ups e baixa consolidação de impacto e valor, "
            "fazendo com que a conversa perca força analítica e fique vulnerável a desvios operacionais."
        )

    if score25 <= 18:
        return (
            "A conversa apresenta uma boa base de execução do método SPIN. "
            "Há direcionamento, perguntas relevantes e início de diagnóstico consultivo. "
            "Entretanto, ainda existem oportunidades claras de evolução, principalmente na quantificação das dores, "
            "na exploração mais profunda das implicações e na conexão explícita entre problema, impacto e benefício."
        )

    if score25 <= 23:
        return (
            "A avaliação indica uma execução forte e consistente do método SPIN. "
            "A conversa demonstra controle de abertura, bom encadeamento de diagnóstico e exploração adequada de impacto. "
            "Como ajuste final, recomenda-se consolidar melhor os critérios de sucesso, "
            "formalizar próximos passos e reforçar a conexão entre valor percebido e decisão."
        )

    return (
        "Excelente execução do método SPIN. "
        "A conversa apresenta enquadramento claro desde a abertura, diagnóstico progressivo e bem estruturado, "
        "exploração consistente de problemas e implicações, e forte conexão entre impacto e valor. "
        "O vendedor atua de forma claramente consultiva, conduzindo a interação com lógica, clareza e foco em decisão."
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
    """
    Feedback didático e profissional por fase do SPIN (inclui Abertura).
    Nota esperada: 0 a 5.
    """
    base = {
        "abertura": [
            "Abertura ausente. Não houve enquadramento mínimo (quem liga, por quê, objetivo e tempo). Sem isso, a conversa tende a ficar reativa e pouco previsível.",
            "Abertura fraca. Houve contato inicial, mas faltou alinhar contexto, confirmar se é um bom momento e estabelecer uma agenda simples (o que será coberto e em quanto tempo).",
            "Abertura adequada, porém incompleta. Recomenda-se explicitar objetivo em 1 frase, validar disponibilidade do cliente e sinalizar o próximo passo esperado ao final da conversa.",
            "Boa abertura. Há introdução e início de alinhamento, mas ainda pode elevar confirmando papel do interlocutor (influenciador/decisor) e combinando agenda curta antes do diagnóstico.",
            "Abertura forte. Enquadramento claro e transição bem feita. Para refinamento: consolidar agenda + tempo, confirmar participantes/decisão e pedir permissão para conduzir 2–3 perguntas-chave.",
            "Abertura excelente. Enquadramento completo (contexto, objetivo, tempo e agenda), com controle de condução e transição natural para diagnóstico consultivo."
        ],
        "situation": [
            "Situação ausente. Não foi coletado o cenário atual (processo, rotina, ferramentas e responsáveis), o que enfraquece a validade do diagnóstico nas fases seguintes.",
            "Situação superficial. Há perguntas iniciais, mas faltam elementos básicos (como funciona hoje, quem faz, com que frequência e quais ferramentas/sistemas são usados).",
            "Situação básica, porém pouco analítica. Para evoluir: incluir quantificação (volume, tempo, frequência), mapear variações/exceções e obter 1 exemplo recente do processo real.",
            "Boa Situação. O cenário está razoavelmente mapeado. Para elevar: registrar números (tempo, volume, taxa de erro) e fechar com um resumo em 1 frase para confirmação do cliente.",
            "Situação muito boa. Há clareza de processo e contexto. Ajuste fino: explorar exceções/regras, pontos de controle e validar o impacto operacional do cenário atual.",
            "Situação excelente. Mapeamento completo e consistente do cenário, com contexto suficiente para sustentar Problema, Implicação e Need-Payoff com precisão."
        ],
        "problem": [
            "Problema ausente. A conversa não explicitou uma dor concreta. Sem problema definido, a discussão tende a virar apresentação de solução sem base diagnóstica.",
            "Problema fraco. Uma dor foi sugerida, mas sem evidências. Para fortalecer: pedir exemplos, localizar onde falha/trava e confirmar frequência e gravidade.",
            "Problema identificado, porém raso. Recomenda-se aprofundar com follow-ups (quando acontece, com que frequência, quem é afetado) e priorizar 1–2 dores principais.",
            "Boa etapa de Problema. A dor aparece com alguma clareza. Para evoluir: transformar a dor em requisito objetivo (o que precisa mudar) e validar prioridade com o cliente.",
            "Problema forte. Dor clara e bem explorada. Ajuste fino: estimar custo/tempo perdido associado e definir critérios do “problema resolvido” (como saberemos que melhorou).",
            "Problema excelente. Dores principais bem definidas, sustentadas por exemplos e priorização clara, criando base sólida para explorar implicações e construir valor."
        ],
        "implication": [
            "Implicação ausente. Não houve exploração das consequências do problema (custo, tempo, risco, qualidade, experiência). Sem impacto, a urgência e o valor ficam frágeis.",
            "Implicação fraca. O impacto foi citado de forma genérica. Para evoluir: detalhar consequências reais, quem é afetado e quais riscos/ineficiências surgem no dia a dia.",
            "Implicação presente, mas pouco consistente. Recomenda-se quantificar (estimativas já ajudam), conectar a metas (prazo, qualidade, receita, compliance) e validar a leitura com o cliente.",
            "Boa Implicação. Há exploração razoável de impacto. Para elevar: escolher 1–2 impactos mais relevantes e aprofundar com números e exemplos concretos.",
            "Implicação forte. Consequências bem conectadas ao contexto. Ajuste fino: resumir impacto em 1 frase e obter confirmação explícita (“faz sentido?”) antes de avançar.",
            "Implicação excelente. Impacto claro, coerente e bem sustentado, aumentando percepção de urgência e preparando o terreno para consolidar valor no Need-Payoff."
        ],
        "need_payoff": [
            "Need-payoff ausente. Não houve consolidação de valor (benefícios desejados, critérios de sucesso ou próximos passos). A conversa encerra sem direção de decisão.",
            "Benefícios genéricos. Há intenção de valor, mas sem ligação direta com a dor/impacto. Para melhorar: transformar benefício em resultado específico e mensurável (mesmo que estimado).",
            "Need-payoff adequado, porém pouco concreto. Recomenda-se explicitar ganhos (tempo, custo, risco), estabelecer critérios de sucesso e sugerir próximo passo objetivo.",
            "Boa etapa de Need-payoff. Valor começa a ficar claro. Para elevar: confirmar prioridade do cliente, critérios de decisão e desenhar próximos passos (quem, quando, o que será validado).",
            "Need-payoff forte. Benefícios bem conectados ao impacto. Ajuste fino: fechar com resumo (dor → impacto → valor) e obter compromisso do próximo passo (reunião, proposta, piloto).",
            "Need-payoff excelente. Valor consolidado com critérios claros, alinhamento de decisão e próximos passos objetivos, demonstrando condução consultiva madura."
        ],
    }

    arr = base.get(fase, ["—"] * 6)
    try:
        n = int(nota)
    except Exception:
        n = 0
    n = max(0, min(5, n))
    return arr[n]
    

def render_avaliacao_completa(filename: str, row: pd.Series):
    phase_scores = build_phase_scores_from_row(row)
    score25 = score_total_25(phase_scores)
    qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)
    msg_geral = msg_geral_por_score25(score25)

    processado_em = str(row.get("processado_em", row.get("avaliado_em", "—")))

    st.markdown(
        f"""
<div class="card">
  <h3 style="margin:0;">{filename}</h3>
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
# 🔁 Execução: TXT (1 item)
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

    st.success(f"✅ Avaliação concluída em {human_time(time.time()-started)}")
    st.download_button(
        "📥 Baixar Excel (avaliação)",
        data=excel_bytes,
        file_name="avaliacao_spin_avancada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    df = normalizar_df(excel_bytes_to_df(excel_bytes))
    st.markdown("---")
    st.markdown("### 📊 Dados (Excel)")
    st.dataframe(df, use_container_width=True)

    # tenta focar no arquivo
    arquivo_foco = str(resp.get("arquivo", fname))
    if "arquivo" in df.columns and (df["arquivo"].astype(str) == arquivo_foco).any():
        row = pick_row_by_file(df, arquivo_foco)
    else:
        row = df.iloc[-1] if not df.empty else None

    if row is not None:
        st.markdown("---")
        st.markdown("## ✅ Resultado detalhado")
        render_avaliacao_completa(arquivo_foco, row)


# ==============================
# 🔁 Execução: WAV (1 item)
# ==============================
def processar_wav_unico(wav_file):
    wav_bytes = wav_file.getbuffer().tobytes()

    # salva temporário para medir duração
    tmp_wav = TMP_WAV / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    tmp_wav.write_bytes(wav_bytes)

    try:
        dur = duracao_wav_seg(tmp_wav)
    except Exception:
        dur = 0.0

    if dur > 600:
        st.error(f"❌ Áudio tem {dur/60:.1f} minutos. Limite recomendado: 10 minutos.")
        return

    started = time.time()
    with st.spinner("Transcrevendo no servidor (VPS)…"):
        data_t = api_transcribe_wav(wav_bytes, filename=wav_file.name)

    text_labeled = (data_t.get("text_labeled") or "").strip()
    if not text_labeled:
        st.error("❌ A transcrição veio vazia.")
        st.json(data_t)
        return

    st.success("✅ Transcrição concluída")
    st.download_button("📥 Baixar TXT (rotulado)", data=text_labeled, file_name="transcricao_rotulada.txt", use_container_width=True)
    st.download_button("📥 Baixar JSON (transcrição)", data=json.dumps(data_t, ensure_ascii=False, indent=2), file_name="transcricao.json", use_container_width=True)

    # agora avalia
    fname = f"painel_wav_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with st.spinner("Avaliando no servidor (VPS)…"):
        resp = api_analyze_text(text_labeled, filename=fname)

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

    st.success(f"✅ Avaliação concluída em {human_time(time.time()-started)}")
    st.download_button(
        "📥 Baixar Excel (avaliação)",
        data=excel_bytes,
        file_name="avaliacao_spin_avancada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    df = normalizar_df(excel_bytes_to_df(excel_bytes))
    st.markdown("---")
    st.markdown("### 📊 Dados (Excel)")
    st.dataframe(df, use_container_width=True)

        arquivo_foco = str(resp.get("arquivo", fname))

    row = pick_row_by_file(df, arquivo_foco)
    if row is None:
        row = df.iloc[-1] if not df.empty else None

    if row is not None:
        st.markdown("---")
        st.markdown("## ✅ Resultado detalhado")
        render_avaliacao_completa(arquivo_foco, row)

# ==============================
# 🔁 Execução: Lote TXT (até 10)
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

        excel_bytes = decode_excel_base64_to_bytes(resp["excel_base64"])
        df = normalizar_df(excel_bytes_to_df(excel_bytes))

        # pega última linha (geralmente 1 ligação)
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
        fname = str(row.get("arquivo", "—"))
        render_avaliacao_completa(fname, row)


# ==============================
# 🔁 Execução: Lote WAV (até 10)
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
        fname = str(row.get("arquivo", "—"))
        render_avaliacao_completa(fname, row)


# ==============================
# ✅ UI: Telas
# ==============================
if st.session_state["view"] == "single":
    st.markdown("### 👤 Avaliação Individual")
    tab_txt, tab_wav = st.tabs(["📝 Colar transcrição (TXT)", "🎧 Enviar áudio (WAV)"])

    with tab_txt:
        exemplo = (
            "[VENDEDOR] Olá, bom dia! Aqui é o Carlos, da MedTech Solutions. Tudo bem?\n"
            "[CLIENTE] Bom dia! Tudo bem.\n"
            "[VENDEDOR] Hoje, como vocês controlam os materiais e implantes? É planilha, sistema ou um processo fixo?\n"
            "[CLIENTE] A gente usa planilhas.\n"
        )
        txt_input = st.text_area("Cole a transcrição aqui", height=260, value=exemplo)

        if st.button("✅ Avaliar texto", use_container_width=True):
            ok, msg = validar_transcricao(txt_input)
            if not ok:
                st.error(msg)
            else:
                limpar_temporarios()
                fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                processar_txt_unico(txt_input, fname)

    with tab_wav:
        up_wav = st.file_uploader("Envie um WAV (até ~10 min)", type=["wav"])
        if st.button("✅ Avaliar áudio", use_container_width=True):
            if up_wav is None:
                st.error("Envie um WAV para continuar.")
            else:
                limpar_temporarios()
                processar_wav_unico(up_wav)

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

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3A4A63;'>"
    "SPIN Analyzer — Projeto Tele_IA 2026 | Desenvolvido por Paulo Coutinho"
    "</div>",
    unsafe_allow_html=True,
)

