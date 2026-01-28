# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT ou Áudio)
# PARTE 1/3 — BASE (helpers + layout + sidebar + render)
# ✅ Mantém modo LOCAL (venvs + scripts)
# ✅ Suporta modo VPS (APIs) quando configurado
# ✅ NÃO inclui telas (Individual / Lote / Resultado) — isso vem na PARTE 2 e 3
# ✅ Removido texto extra (Secrets/Cloud) do painel
# ===============================================

import os
import sys
import re
import time
import shutil
import subprocess
import wave
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

# requests opcional (necessário para modo VPS)
try:
    import requests
except Exception:
    requests = None


# ==============================
# ⚙️ Página
# ==============================
st.set_page_config(
    page_title="SPIN Analyzer — Avaliação de Ligações",
    page_icon="🎧",
    layout="wide",
)


# ==============================
# 🎨 Visual profissional (CLARO + sem transparência)
# ==============================
st.markdown(
    """
<style>
:root{
  --bg: #FFFFFF;
  --text: #0B1220;
  --muted: #3A4A63;

  --card: #FFFFFF;
  --card2: #F6F9FF;

  --stroke: #C7D6F5;
  --stroke2: #AFC7F3;

  --accent: #0B63F3;
  --accentDark: #0A47A8;

  --okBg: #E6FFF3;
  --okStroke: #29B37C;
  --okText: #0B6B4B;

  --warnBg: #FFF5D6;
  --warnStroke: #D39B00;
  --warnText: #7A5600;

  --badBg: #FFE7EC;
  --badStroke: #E64664;
  --badText: #9E1230;

  --shadow: 0 8px 24px rgba(11,18,32,0.08);
}

html, body, [class*="css"]{
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
}
section.main > div { background: var(--bg) !important; }

.block-container{
  padding-top: 1.2rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
}

h1,h2,h3{
  color: var(--accentDark) !important;
  letter-spacing: 0.2px;
}
.small-muted{
  color: var(--muted);
  font-size: 0.98rem;
  line-height: 1.55;
}
.hr{
  height: 1px;
  background: #E4ECFF;
  margin: 16px 0;
}

.metric{
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
}
.metric .label{
  color: var(--muted);
  font-size: 0.92rem;
  margin-bottom: 6px;
  font-weight: 700;
}
.metric .value{
  color: var(--text);
  font-size: 2.1rem;
  font-weight: 900;
  line-height: 1.0;
}

.badge{
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--stroke2);
  background: var(--card2);
  color: var(--accent);
  font-weight: 900;
  font-size: 0.9rem;
}

.card{
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 18px;
  margin-bottom: 14px;
  box-shadow: var(--shadow);
}
.card-title{
  font-size: 1.05rem;
  font-weight: 900;
  color: var(--text);
  margin: 0 0 10px 0;
}

.lead{
  color: var(--text) !important;
  font-size: 1.02rem;
  line-height: 1.6;
}

.pill-row{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin: 8px 0 10px 0;
}
.pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--stroke2);
  background: var(--card2);
  font-weight: 900;
}
.pill .k{
  color: var(--muted);
  font-weight: 900;
}
.pill .v{
  color: var(--text);
  font-weight: 1000;
}

.grid2{
  display:grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 12px;
}
@media (max-width: 900px){
  .grid2{ grid-template-columns: 1fr; }
}

.block{
  background: var(--card2);
  border: 1px solid var(--stroke2);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
}
.block h4{
  margin: 0 0 8px 0;
  font-size: 0.98rem;
  font-weight: 1000;
  color: var(--accent);
}
.block p{
  margin: 0;
  color: var(--text);
  line-height: 1.6;
  font-size: 1.0rem;
}

.tag{
  display:inline-block;
  padding: 5px 10px;
  border-radius: 999px;
  border: 2px solid var(--stroke2);
  background: var(--card2);
  color: var(--accent);
  font-weight: 1000;
  font-size: 0.88rem;
}
.tag.ok{
  background: var(--okBg);
  border-color: var(--okStroke);
  color: var(--okText);
}
.tag.warn{
  background: var(--warnBg);
  border-color: var(--warnStroke);
  color: var(--warnText);
}
.tag.bad{
  background: var(--badBg);
  border-color: var(--badStroke);
  color: var(--badText);
}

textarea, input, .stTextArea textarea{
  background: #FFFFFF !important;
  color: var(--text) !important;
  border-radius: 12px !important;
  border: 1px solid var(--stroke2) !important;
}

.stButton > button{
  background: var(--accent) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 12px !important;
  padding: 10px 14px !important;
  font-weight: 900 !important;
}
.stButton > button:hover{ background: #0A56D6 !important; }

pre{
  background: #0B1220 !important;
  color: #EAF0FF !important;
  border: 1px solid #1D2B4A !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==============================
# 📂 Paths do projeto
# ==============================
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
SCRIPTS_DIR = ROOT_DIR / "scripts_base"

TXT_DIR = ROOT_DIR / "arquivos_transcritos" / "txt"
TXT_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = ROOT_DIR / "_painel_uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_WAV_DIR = UPLOADS_DIR / "wav"
UPLOADS_WAV_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = ROOT_DIR / "_painel_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

RESULTADOS_SPIN = ROOT_DIR / "saida_excel" / "resultados_completos_SPIN.xlsx"
AVALIACAO_SPIN = ROOT_DIR / "saida_avaliacao" / "excel" / "avaliacao_spin_avancada.xlsx"

SCRIPT_01 = SCRIPTS_DIR / "01_transcricao.py"
SCRIPT_02 = SCRIPTS_DIR / "02_zeroshot.py"


def achar_script_03() -> Path | None:
    if not SCRIPTS_DIR.exists():
        return None
    candidatos = sorted(SCRIPTS_DIR.glob("03_*.py"))
    return candidatos[0] if candidatos else None


SCRIPT_03 = achar_script_03()


# ==============================
# 🧠 Seleção de Python por etapa (LOCAL)
# ==============================
def pick_python_for_transcription_auto() -> Path | None:
    env = os.getenv("TRANSCRIBE_PYTHON")
    if env and Path(env).exists():
        return Path(env)

    candidates = [
        ROOT_DIR / ".venv_transcricao" / "Scripts" / "python.exe",
        ROOT_DIR / ".venv_whisperx" / "Scripts" / "python.exe",
        ROOT_DIR / ".venv_metricas" / "Scripts" / "python.exe",
        ROOT_DIR / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def pick_python_for_zeroshot() -> Path:
    env = os.getenv("ZEROSHOT_PYTHON")
    if env and Path(env).exists():
        return Path(env)

    c = ROOT_DIR / ".venv_zeroshot" / "Scripts" / "python.exe"
    if c.exists():
        return c

    return Path(sys.executable)


PY_ZEROSHOT = pick_python_for_zeroshot()


# ==============================
# 🔧 Execução segura (LOCAL)
# ==============================
def run_cmd(python_exe: Path, script: Path, args: list[str], cwd: Path, timeout_s: int) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [str(python_exe), "-X", "utf8", str(script)] + args

    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            env=env,
            timeout=timeout_s,
        )
        out = (p.stdout or "")
        if p.stderr:
            out += "\n" + p.stderr
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, "Tempo limite excedido. Tente novamente com um texto menor ou um áudio mais curto."
    except Exception:
        return 1, "Não foi possível processar no modo local. Verifique se o ambiente foi instalado corretamente."


def wav_duracao_seg(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate <= 0:
            return 0.0
        return frames / float(rate)


# ==============================
# 🌐 VPS — helpers (sem expor textos extras no painel)
# ==============================
def get_transcribe_vps_url() -> str:
    url = os.getenv("TRANSCRIBE_API_URL", "").strip()
    try:
        if not url and hasattr(st, "secrets"):
            url = str(st.secrets.get("TRANSCRIBE_API_URL", "")).strip()
    except Exception:
        pass
    return url


def get_analyze_vps_url() -> str:
    url = os.getenv("ANALYZE_API_URL", "").strip()
    try:
        if not url and hasattr(st, "secrets"):
            url = str(st.secrets.get("ANALYZE_API_URL", "")).strip()
    except Exception:
        pass
    return url


def transcribe_vps_wav_to_labeled_text(wav_bytes: bytes, filename: str = "audio.wav") -> dict:
    if requests is None:
        raise RuntimeError("Dependência 'requests' não instalada.")
    url = get_transcribe_vps_url()
    if not url:
        raise RuntimeError("TRANSCRIBE_API_URL não configurado.")
    files = {"file": (filename, wav_bytes, "audio/wav")}
    r = requests.post(url, files=files, timeout=600)
    r.raise_for_status()
    return r.json()


def analyze_vps_text(text_labeled: str, filename: str) -> dict:
    if requests is None:
        raise RuntimeError("Dependência 'requests' não instalada.")
    url = get_analyze_vps_url()
    if not url:
        raise RuntimeError("ANALYZE_API_URL não configurado.")
    payload = {"text_labeled": text_labeled, "filename": filename}
    r = requests.post(url, json=payload, timeout=7200)
    r.raise_for_status()
    return r.json()


def save_transcription_to_txt_dir(text_labeled: str, prefix: str) -> Path:
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    out_path = TXT_DIR / fname
    out_path.write_text(text_labeled.strip() + "\n", encoding="utf-8")
    return out_path


# ==============================
# 🔒 Isolamento (para não misturar TXT do painel com TXT do projeto)
# ==============================
def backup_txts_existentes() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"txt_{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for f in TXT_DIR.glob("*.txt"):
        shutil.move(str(f), str(dest / f.name))
    return dest


def restore_txts(backup_path: Path):
    if not backup_path.exists():
        return
    for f in backup_path.glob("*.txt"):
        shutil.move(str(f), str(TXT_DIR / f.name))


def cleanup_backup_dir(backup_path: Path):
    try:
        if backup_path and backup_path.exists():
            if not any(backup_path.iterdir()):
                shutil.rmtree(backup_path, ignore_errors=True)
    except Exception:
        pass


# ==============================
# 📊 Carregar resultados
# ==============================
def carregar_resultado_final() -> pd.DataFrame | None:
    if AVALIACAO_SPIN.exists():
        try:
            df = pd.read_excel(AVALIACAO_SPIN)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

    if RESULTADOS_SPIN.exists():
        try:
            df = pd.read_excel(RESULTADOS_SPIN)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

    return None


def normalizar_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["arquivo"] = df["arquivo"].astype(str) if "arquivo" in df.columns else ""

    for col in ["nota_final", "pontuacao_total", "pontuacao_base"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df.rename(
        columns={
            "implicacao_feedback": "implication_feedback",
            "necessidade_feedback": "need_payoff_feedback",
        },
        inplace=True,
    )
    return df


def get_df_resultados() -> pd.DataFrame | None:
    df = carregar_resultado_final()
    if df is None or df.empty:
        return None
    return normalizar_df(df)


def filtrar_df_por_arquivos(df: pd.DataFrame, arquivos: list[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    s = set(str(a) for a in arquivos)
    return df[df["arquivo"].astype(str).isin(s)].copy()


def pick_row_by_file(df: pd.DataFrame, filename: str) -> pd.Series | None:
    if df is None or df.empty:
        return None
    dff = df[df["arquivo"].astype(str) == str(filename)]
    if dff.empty:
        return None
    return dff.iloc[-1]


# ==============================
# ✅ Validação do TXT
# ==============================
def validar_txt(txt: str) -> tuple[bool, str]:
    linhas = [l.strip() for l in txt.splitlines() if l.strip()]
    if len(linhas) < 4:
        return False, "O texto está muito curto. Cole uma conversa com várias falas."
    has_tag = any(re.match(r"^\[(VENDEDOR|CLIENTE)\]", l, re.IGNORECASE) for l in linhas)
    if not has_tag:
        return False, "Formato inválido. Use linhas começando com [VENDEDOR] e [CLIENTE]."
    return True, "ok"


# ==============================
# ✅ Progresso
# ==============================
def human_time(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s"


def progresso(total_steps: int):
    bar = st.progress(0)
    status = st.empty()
    clock = st.empty()
    return bar, status, clock


def progresso_update(bar, status, clock, step_idx: int, total_steps: int, title: str, started_at: float):
    frac = min(max(step_idx / total_steps, 0.0), 1.0)
    bar.progress(frac)
    status.markdown(f"**{title}**")
    clock.markdown(
        f"<div class='small-muted'>⏱️ Tempo decorrido: <b>{human_time(time.time()-started_at)}</b></div>",
        unsafe_allow_html=True,
    )


# ==============================
# 🧩 Avaliação (mensagens programadas)
# ==============================
def clamp_int(x, lo, hi, default=0):
    try:
        v = int(float(x))
        return max(lo, min(hi, v))
    except Exception:
        return default


def score_total_25(phase_scores: dict) -> int:
    return sum(clamp_int(phase_scores.get(k, 0), 0, 5) for k in ["abertura", "situation", "problem", "implication", "need_payoff"])


def msg_geral_por_score25(score25: int) -> str:
    if score25 <= 6:
        return (
            "Pontuação muito baixa no método (Abertura + SPIN). A conversa tende a ficar reativa/operacional, "
            "com pouco controle de agenda e pouco diagnóstico consultivo."
        )
    if score25 <= 12:
        return (
            "Há sinais iniciais de estrutura consultiva, mas a execução é irregular. "
            "O diagnóstico aparece em partes, com falta de follow-ups e pouca consolidação de impacto e valor."
        )
    if score25 <= 18:
        return (
            "Boa base de execução. A conversa tem direção e diagnóstico, mas ainda pode elevar consistência "
            "com quantificação e melhor consolidação de valor."
        )
    if score25 <= 23:
        return (
            "Execução muito forte. A conversa segue lógica clara, com bom controle de abertura e exploração de dor/impacto. "
            "Para ficar excelente: consolidar necessidade-benefício com métricas e próximos passos bem definidos."
        )
    return (
        "Excelente execução (Abertura + SPIN). A conversa demonstra domínio: enquadramento inicial claro, "
        "diagnóstico progressivo e conexão objetiva entre dor, impacto e benefícios desejados."
    )


def label_qualidade_por_score25(score25: int) -> tuple[str, str]:
    if score25 <= 8:
        return "Baixa", "bad"
    if score25 <= 18:
        return "Moderada", "warn"
    return "Alta", "ok"


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


def tag_class_por_nota(nota: int) -> str:
    if nota >= 4:
        return "ok"
    if nota == 3:
        return "warn"
    return "bad"


def feedback_programado(fase: str, nota: int) -> str:
    if fase == "abertura":
        if nota == 0:
            return "A abertura não ficou clara. Sem enquadramento inicial, a conversa perde direção e previsibilidade."
        if nota == 1:
            return "A abertura foi fraca: faltou apresentar-se, contextualizar o motivo do contato e alinhar tempo/objetivo."
        if nota == 2:
            return "A abertura existe, mas poderia ser mais profissional: apresentar → confirmar se é um bom momento → alinhar agenda e tempo."
        if nota == 3:
            return "Boa abertura. Para elevar: confirmar papel do interlocutor e pedir permissão para duas perguntas objetivas."
        if nota == 4:
            return "Abertura bem conduzida. Ajuste fino: agenda em 1 frase + confirmação do decisor/participantes."
        return "Abertura excelente: enquadramento completo e transição suave para diagnóstico."

    if fase == "situation":
        if nota == 0:
            return "Não houve mapeamento do cenário atual. Sem Situação, o diagnóstico fica genérico e pouco confiável."
        if nota == 1:
            return "Perguntas situacionais superficiais. Faltaram processo atual, ferramentas, responsáveis e rotina do cliente."
        if nota == 2:
            return "Você coletou o básico, mas faltaram follow-ups: volumes, frequência, exceções e critérios de controle atuais."
        if nota == 3:
            return "Boa Situação. Para elevar: quantificar e pedir exemplos recentes."
        if nota == 4:
            return "Situação bem explorada. Ajuste fino: resumir o cenário em 1 frase e pedir confirmação do cliente."
        return "Situação excelente: processo e contexto bem mapeados, sustentando as próximas fases."

    if fase == "problem":
        if nota == 0:
            return "O problema não ficou claro. Sem dor específica, a conversa tende a virar apresentação de solução."
        if nota == 1:
            return "Identificação de problema fraca. Faltaram perguntas sobre o que falha, onde trava e com que frequência."
        if nota == 2:
            return "Há tentativa, mas pouca profundidade. Sugestão: pedir casos reais e validar frequência/gravidade."
        if nota == 3:
            return "Boa etapa de Problema. Para melhorar: priorizar 1–2 dores e confirmar qual é a mais crítica."
        if nota == 4:
            return "Problema bem conduzido: dor clara e investigada. Ajuste fino: transformar dor em requisito objetivo."
        return "Problema excelente: dores principais reveladas com clareza, exemplos e priorização."

    if fase == "implication":
        if nota == 0:
            return "Não houve exploração de implicações. Sem impacto, o cliente não percebe urgência nem valor."
        if nota == 1:
            return "Implicação pouco explorada. Faltaram consequências: custo, tempo, risco e experiência."
        if nota == 2:
            return "Você tocou no impacto, mas sem aprofundar. Sugestão: quantificar e ligar a metas do negócio."
        if nota == 3:
            return "Boa implicação. Para elevar: escolher o impacto principal e validar com o cliente."
        if nota == 4:
            return "Implicação bem construída. Ajuste fino: resumir o impacto e confirmar a leitura com o cliente."
        return "Implicação excelente: consequências claras e conectadas a objetivos reais."

    if fase == "need_payoff":
        if nota == 0:
            return "Necessidade-benefício não apareceu. Sem isso, não há consolidação de valor nem critérios de sucesso."
        if nota == 1:
            return "Benefícios genéricos. Faltou conectar necessidades específicas a resultados desejados."
        if nota == 2:
            return "Você tentou falar de valor, mas ainda ficou pouco concreto. Sugestão: ganhos mensuráveis."
        if nota == 3:
            return "Boa necessidade-benefício. Para elevar: critérios de sucesso e próximo passo com decisores."
        if nota == 4:
            return "Need-payoff bem feito. Ajuste fino: fechar com resumo de valor + compromisso de próximo passo."
        return "Need-payoff excelente: valor verbalizado, critérios claros e próximos passos alinhados."

    return "Feedback indisponível para esta fase."


def extracao_programada(fase: str, nota: int) -> str:
    if fase == "abertura":
        if nota == 0:
            return "Não foram coletados dados de enquadramento (objetivo, tempo disponível e interlocutor correto)."
        if nota == 1:
            return "Dados iniciais insuficientes: faltou objetivo/agenda e validação do papel do interlocutor."
        if nota == 2:
            return "Alguns dados aparecem, mas ainda faltam: tempo/agenda e confirmação do responsável/decisor."
        if nota == 3:
            return "Boa extração inicial: contexto e direção. Pode melhorar registrando agenda e quem participa da decisão."
        if nota == 4:
            return "Extração sólida: objetivo, tempo e papel do interlocutor. Ajuste: explicitar próximos passos esperados."
        return "Extração excelente: contexto, agenda, tempo, interlocutor correto e transição clara."

    if fase == "situation":
        if nota == 0:
            return "Não foram coletados dados do cenário atual (processo, ferramenta, rotina, responsáveis)."
        if nota == 1:
            return "Dados mínimos: faltaram processo, volumes, frequência e responsáveis."
        if nota == 2:
            return "Alguns dados aparecem, mas faltam métricas e critérios (volume/tempo, exceções, regras)."
        if nota == 3:
            return "Dados relevantes coletados. Para fortalecer: números e exemplos recentes."
        if nota == 4:
            return "Boa extração do cenário. Ajuste fino: registrar métricas e variações do processo."
        return "Extração excelente: cenário completo, com processo, responsáveis e métricas úteis."

    if fase == "problem":
        if nota == 0:
            return "Não foram coletados problemas específicos nem exemplos do que falha."
        if nota == 1:
            return "Problemas pouco claros: faltaram exemplos, frequência e pontos de falha."
        if nota == 2:
            return "Problemas foram citados, mas faltam evidências: casos recentes e frequência/gravidade."
        if nota == 3:
            return "Boa extração de dor. Para elevar: priorizar 1–2 dores e definir critérios do que precisa mudar."
        if nota == 4:
            return "Extração forte: dores claras e investigadas. Ajuste: transformar em requisitos objetivos."
        return "Extração excelente: dores principais, exemplos concretos e priorização bem definida."

    if fase == "implication":
        if nota == 0:
            return "Não foram coletados dados de impacto (custos, riscos, tempo perdido, reputação)."
        if nota == 1:
            return "Impacto pouco explorado: faltaram consequências e quem é afetado."
        if nota == 2:
            return "Algum impacto apareceu, mas sem quantificação."
        if nota == 3:
            return "Boa extração de impacto. Para elevar: números/estimativas e ligação com metas."
        if nota == 4:
            return "Extração muito boa. Ajuste: priorizar o impacto principal e validar com o cliente."
        return "Extração excelente: impactos claros, coerentes e, quando possível, quantificados."

    if fase == "need_payoff":
        if nota == 0:
            return "Não foram coletados critérios de sucesso nem benefícios desejados."
        if nota == 1:
            return "Benefícios genéricos. Faltou ligar a dor a resultados e critérios objetivos."
        if nota == 2:
            return "Algum valor foi discutido, mas sem métricas e prioridade do cliente."
        if nota == 3:
            return "Boa extração de valor. Para elevar: critérios de decisão e próximo passo com decisores."
        if nota == 4:
            return "Extração forte. Ajuste: consolidar critérios de sucesso e compromisso de próximo passo."
        return "Extração excelente: valor claro, critérios de sucesso definidos e próximos passos alinhados."

    return "Extração de dados indisponível para esta fase."


# ==============================
# ✅ Tratamento do erro de memória (LOCAL)
# ==============================
def is_oom_mkl(err_text: str) -> bool:
    t = (err_text or "").lower()
    return ("mkl_malloc" in t and "failed to allocate memory" in t) or ("failed to allocate memory" in t)


def transcribe_with_fallback(py_transcribe: Path, run_dir: Path, model_choice: str, diar: bool) -> tuple[int, str, str]:
    args01 = ["--input_dir", str(run_dir), "--model", model_choice, "--language", "pt"]
    if diar:
        args01.append("--enable_diarization")

    rc1, out1 = run_cmd(py_transcribe, SCRIPT_01, args01, ROOT_DIR, timeout_s=7200)
    if rc1 == 0:
        return rc1, out1, model_choice

    if model_choice != "small" and is_oom_mkl(out1):
        args01b = ["--input_dir", str(run_dir), "--model", "small", "--language", "pt"]
        if diar:
            args01b.append("--enable_diarization")
        rc2, out2 = run_cmd(py_transcribe, SCRIPT_01, args01b, ROOT_DIR, timeout_s=7200)
        return rc2, out2, "small"

    return rc1, out1, model_choice


# ==============================
# 🧭 Navegação interna (2 painéis)
# ==============================
if "view" not in st.session_state:
    st.session_state["view"] = "single"  # single | batch


def go_single():
    st.session_state["view"] = "single"
    st.rerun()


def go_batch():
    st.session_state["view"] = "batch"
    st.rerun()


# ==============================
# Sidebar: navegação + config local + status VPS
# (sem textos extras para o cliente)
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")
    c1, c2 = st.columns(2)
    with c1:
        st.button("👤 Individual", use_container_width=True, on_click=go_single)
    with c2:
        st.button("📊 Visão Gerencial", use_container_width=True, on_click=go_batch)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    with st.expander("⚙️ Configuração do Áudio (LOCAL)", expanded=False):
        st.markdown(
            "<div class='small-muted'>Se o áudio falhar no modo local, informe o Python do ambiente "
            "<b>.venv_transcricao</b>.</div>",
            unsafe_allow_html=True,
        )
        manual_py01 = st.text_input(
            "Python da transcrição (opcional)",
            value=st.session_state.get("manual_py01", ""),
            placeholder=r"Ex: C:\Projeto...\ .venv_transcricao\Scripts\python.exe",
            key="manual_py01_input",
        )
        if manual_py01.strip():
            st.session_state["manual_py01"] = manual_py01.strip()

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.markdown("### 🌐 Status do Servidor")

    vps_t_url = get_transcribe_vps_url()
    vps_a_url = get_analyze_vps_url()
    vps_ok = bool(vps_t_url) and bool(vps_a_url) and (requests is not None)

    if vps_ok:
        st.success("Servidor conectado ✅")
    else:
        st.info("Servidor não configurado (modo local disponível).")


# ==============================
# Detectar PY_TRANSCRIBE local
# ==============================
PY_TRANSCRIBE = None
if st.session_state.get("manual_py01"):
    p = Path(st.session_state["manual_py01"])
    if p.exists():
        PY_TRANSCRIBE = p
if PY_TRANSCRIBE is None:
    PY_TRANSCRIBE = pick_python_for_transcription_auto()


# ==============================
# Cabeçalho
# ==============================
st.markdown("## 🎧 SPIN Analyzer — Avaliação de Ligações")
st.markdown(
    "<div class='small-muted'>Cole transcrição <b>[VENDEDOR]</b>/<b>[CLIENTE]</b> ou envie WAV. "
    "Use <b>Individual</b> para 1 ligação e <b>Visão Gerencial</b> para até 10 entradas.</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)


# ==============================
# Render helpers
# ==============================
def build_phase_scores_from_row(row: pd.Series) -> dict:
    return {
        "abertura": clamp_int(row.get("abertura_nota_humana", 0), 0, 5),
        "situation": clamp_int(row.get("situation_nota_humana", 0), 0, 5),
        "problem": clamp_int(row.get("problem_nota_humana", 0), 0, 5),
        "implication": clamp_int(row.get("implication_nota_humana", 0), 0, 5),
        "need_payoff": clamp_int(row.get("need_payoff_nota_humana", 0), 0, 5),
    }


def render_avaliacao_completa(filename: str, row: pd.Series):
    phase_scores = build_phase_scores_from_row(row)
    score25 = score_total_25(phase_scores)
    qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)
    msg_geral = msg_geral_por_score25(score25)
    processado_em = str(row.get("processado_em", row.get("avaliado_em", "—")))

    st.markdown(
        f"""
<div class="card">
  <div class="card-title">📄 {filename}</div>
  <div class="pill-row">
    <span class="pill"><span class="k">Pontuação Total</span> <span class="v">{score25}/25</span></span>
    <span class="tag {qualidade_tag}">{qualidade_label}</span>
    <span class="pill"><span class="k">Data/Hora</span> <span class="v">{processado_em}</span></span>
  </div>
  <div class="lead">{msg_geral}</div>
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
        tc = tag_class_por_nota(nota)
        fb = feedback_programado(key, nota)
        ex = extracao_programada(key, nota)

        tag_txt = (
            "Excelente" if nota == 5 else
            "Bom" if nota == 4 else
            "Intermediário" if nota == 3 else
            "Iniciante" if nota in (1, 2) else
            "Ausente"
        )

        st.markdown(
            f"""
<div class="card">
  <div class="card-title">{label}</div>
  <div class="pill-row">
    <span class="pill"><span class="k">Nota</span> <span class="v">{nota}/5</span></span>
    <span class="pill"><span class="k">Ranking</span> <span class="v">{rank}</span></span>
    <span class="tag {tc}">{tag_txt}</span>
  </div>
  <div class="grid2">
    <div class="block">
      <h4>Feedback</h4>
      <p>{fb}</p>
    </div>
    <div class="block">
      <h4>Evidências</h4>
      <p>{ex}</p>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

# ========= FIM DA PARTE 1/3 =========

# ===============================================
# PARTE 2/3 — TELA: INDIVIDUAL (TXT + WAV)
# ===============================================

# ==============================
# Helpers específicos do painel
# ==============================
def require_local_scripts_for_analysis():
    """Garante que o modo local tem os scripts necessários."""
    if not SCRIPT_02.exists():
        st.error("O módulo de análise local não está disponível neste ambiente.")
        st.stop()
    if not SCRIPT_03 or not SCRIPT_03.exists():
        st.error("O módulo de nota local não está disponível neste ambiente.")
        st.stop()


def show_result_after_run(prefer_file: str | None = None):
    """
    Mostra a avaliação detalhada:
    - se prefer_file existir no Excel -> mostra ele
    - senão mostra o mais recente do Excel
    """
    df = get_df_resultados()
    if df is None or df.empty:
        st.warning("Ainda não há resultados para mostrar.")
        return

    if "arquivo" not in df.columns or df["arquivo"].astype(str).nunique() == 0:
        st.warning("O Excel não possui coluna 'arquivo' para detalhamento.")
        return

    arquivo_foco = None

    if prefer_file:
        row = pick_row_by_file(df, prefer_file)
        if row is not None:
            arquivo_foco = prefer_file
        else:
            arquivo_foco = None

    if arquivo_foco is None:
        # tenta o último arquivo (última linha)
        try:
            arquivo_foco = str(df.iloc[-1]["arquivo"])
        except Exception:
            arquivo_foco = None

    if not arquivo_foco:
        st.warning("Não foi possível identificar o arquivo para detalhamento.")
        return

    row = pick_row_by_file(df, arquivo_foco)
    if row is None:
        st.warning("Não encontrei os dados dessa ligação no Excel.")
        return

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.markdown("## ✅ Resultado da avaliação")
    render_avaliacao_completa(str(arquivo_foco), row)


# ==============================
# TELA: INDIVIDUAL
# ==============================
if st.session_state["view"] == "single":
    tab_txt, tab_wav = st.tabs(["📝 Colar transcrição (TXT)", "🎧 Enviar áudio (WAV)"])

    # ---------- TXT ----------
    with tab_txt:
        st.markdown("### 📝 Avaliar a partir do texto")
        st.markdown(
            "<div class='small-muted'>Cole uma conversa com linhas iniciando por <b>[VENDEDOR]</b> e <b>[CLIENTE]</b>.</div>",
            unsafe_allow_html=True,
        )

        exemplo = (
            "[VENDEDOR] Olá, bom dia! Aqui é o Carlos, da MedTech Solutions. Tudo bem?\n"
            "[CLIENTE] Bom dia! Tudo bem.\n"
            "[VENDEDOR] Hoje, como vocês controlam os materiais e implantes? É planilha, sistema ou um processo fixo?\n"
            "[CLIENTE] A gente usa planilhas.\n"
        )
        txt_input = st.text_area("Cole a transcrição aqui", height=260, value=exemplo, key="txt_input")

        if st.button("✅ Avaliar texto", use_container_width=True, key="btn_txt"):
            ok, msg = validar_txt(txt_input)
            if not ok:
                st.error(msg)
                st.stop()

            # Decide VPS vs Local (silencioso)
            use_vps = bool(get_analyze_vps_url()) and (requests is not None)

            if not use_vps:
                require_local_scripts_for_analysis()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=2)

            arquivo_gerado = None
            fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            try:
                # cria o txt temporário para manter compatibilidade com o pipeline
                (TXT_DIR / fname).write_text(txt_input.strip() + "\n", encoding="utf-8")

                progresso_update(bar, status, clock, 1, 2, "Processando a avaliação…", started)

                if use_vps:
                    # VPS avalia direto com o texto rotulado
                    try:
                        resp = analyze_vps_text(txt_input.strip(), filename=fname)
                        if not resp.get("ok"):
                            st.error("Não foi possível avaliar este texto no momento. Tente novamente.")
                            st.stop()
                        arquivo_gerado = str(resp.get("arquivo", fname))
                    except Exception:
                        st.error("Não foi possível conectar ao servidor de avaliação. Tente novamente.")
                        st.stop()

                else:
                    # Local: roda 02 e 03
                    rc2, _ = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=3600)
                    if rc2 != 0:
                        st.error("Não foi possível avaliar este texto no modo local.")
                        st.stop()

                    rc3, _ = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=3600)
                    if rc3 != 0:
                        st.error("Não foi possível finalizar a nota no modo local.")
                        st.stop()

                    arquivo_gerado = fname

                progresso_update(bar, status, clock, 2, 2, "Carregando resultados…", started)

                bar.progress(1.0)
                status.markdown("**✅ Avaliação concluída!**")
                clock.markdown(
                    f"<div class='small-muted'>⏱️ Tempo total: <b>{human_time(time.time()-started)}</b></div>",
                    unsafe_allow_html=True,
                )

                # Guardar referência para a tela Resultado (parte 3 também usa isso)
                st.session_state["last_processed_files"] = [arquivo_gerado] if arquivo_gerado else []
                st.session_state["last_run_done"] = True

                # Mostra resultado já aqui (pra não parecer que travou)
                show_result_after_run(prefer_file=arquivo_gerado)

            finally:
                # limpa txt temporário do painel
                try:
                    for f in TXT_DIR.glob("painel_txt_*.txt"):
                        try:
                            f.unlink()
                        except Exception:
                            pass
                except Exception:
                    pass

                # restaura TXT do projeto
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass

    # ---------- WAV ----------
    with tab_wav:
        st.markdown("### 🎧 Avaliar a partir de um áudio (WAV)")
        st.markdown(
            "<div class='small-muted'>Envie um WAV de até 10 minutos. "
            "Se o servidor estiver conectado, o modo VPS é o mais recomendado.</div>",
            unsafe_allow_html=True,
        )

        up_wav = st.file_uploader("Arquivo WAV", type=["wav"], key="uploader_wav_single")

        vps_disponivel = bool(get_transcribe_vps_url()) and bool(get_analyze_vps_url()) and (requests is not None)

        fonte_transcricao = st.selectbox(
            "Fonte da transcrição",
            ["Local (seu 01_transcricao.py)", "VPS (recomendado)"] if vps_disponivel else ["Local (seu 01_transcricao.py)"],
            index=0,
            key="fonte_transcricao_single",
        )

        model_choice = st.selectbox(
            "Qualidade da transcrição (LOCAL) — recomendado: small",
            ["small", "base", "medium"],
            index=0,
            key="model_choice_single",
        )
        diar = st.checkbox("Tentar diarização (LOCAL)", value=True, key="diarize_single")

        if fonte_transcricao.startswith("VPS") and vps_disponivel:
            st.markdown("<span class='badge'>Servidor ativo</span>", unsafe_allow_html=True)

        if st.button("✅ Avaliar áudio", use_container_width=True, key="btn_wav_single"):
            if up_wav is None:
                st.error("Envie um arquivo WAV para continuar.")
                st.stop()

            # Se NÃO for VPS, precisa scripts locais (02/03)
            if not fonte_transcricao.startswith("VPS"):
                require_local_scripts_for_analysis()

            # salva WAV temporário
            run_dir = UPLOADS_WAV_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_dir.mkdir(parents=True, exist_ok=True)
            wav_path = run_dir / "audio.wav"
            wav_path.write_bytes(up_wav.getbuffer())

            # valida duração
            try:
                dur = wav_duracao_seg(wav_path)
            except Exception:
                dur = 0.0
            if dur > 600:
                st.error(f"O áudio tem {dur/60:.1f} minutos. O limite é 10 minutos.")
                try:
                    shutil.rmtree(run_dir, ignore_errors=True)
                except Exception:
                    pass
                st.stop()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=3)

            arquivo_gerado = None

            try:
                progresso_update(bar, status, clock, 1, 3, "Transcrevendo o áudio…", started)

                # ===== VPS =====
                if fonte_transcricao.startswith("VPS"):
                    try:
                        wav_bytes = up_wav.getbuffer().tobytes()
                        data_vps = transcribe_vps_wav_to_labeled_text(wav_bytes, filename=up_wav.name)
                        text_labeled = (data_vps.get("text_labeled") or "").strip()

                        if not text_labeled:
                            st.error("A transcrição veio vazia. Tente novamente com outro áudio.")
                            st.stop()

                        out_txt_path = save_transcription_to_txt_dir(text_labeled, prefix="painel_wav_vps")

                        # Entregáveis (somente quando VPS)
                        st.download_button("📥 Baixar WAV", data=wav_bytes, file_name=up_wav.name)
                        st.download_button("📥 Baixar TXT (rotulado)", data=text_labeled, file_name="transcricao_rotulada.txt")
                        st.download_button(
                            "📥 Baixar JSON",
                            data=json.dumps(data_vps, ensure_ascii=False, indent=2),
                            file_name="transcricao_vps.json",
                        )

                        progresso_update(bar, status, clock, 2, 3, "Avaliando a ligação…", started)

                        resp = analyze_vps_text(text_labeled, filename=str(out_txt_path.name))
                        if not resp.get("ok"):
                            st.error("Não foi possível avaliar este áudio no momento. Tente novamente.")
                            st.stop()

                        arquivo_gerado = str(resp.get("arquivo", out_txt_path.name))

                    except Exception:
                        st.error("Não foi possível conectar ao servidor. Tente novamente.")
                        st.stop()

                # ===== LOCAL =====
                else:
                    if PY_TRANSCRIBE is None or not Path(PY_TRANSCRIBE).exists():
                        st.error("Modo local não configurado. Configure o Python da transcrição na lateral.")
                        st.stop()

                    if not SCRIPT_01.exists():
                        st.error("Módulo de transcrição local não encontrado.")
                        st.stop()

                    rc1, out1, _ = transcribe_with_fallback(Path(PY_TRANSCRIBE), run_dir, model_choice, diar)
                    if rc1 != 0:
                        if is_oom_mkl(out1):
                            st.error("Falta de memória ao transcrever localmente. Use o modelo small ou envie um áudio menor.")
                        else:
                            st.error("Não foi possível transcrever o áudio no modo local.")
                        st.stop()

                    progresso_update(bar, status, clock, 2, 3, "Analisando SPIN…", started)

                    rc2, _ = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=7200)
                    if rc2 != 0:
                        st.error("Não foi possível avaliar a conversa no modo local.")
                        st.stop()

                    progresso_update(bar, status, clock, 3, 3, "Finalizando a nota…", started)

                    rc3, _ = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=7200)
                    if rc3 != 0:
                        st.error("Não foi possível finalizar a nota no modo local.")
                        st.stop()

                    # No local, a referência de arquivo pode não bater com precisão; usamos o mais recente depois.
                    arquivo_gerado = None

                bar.progress(1.0)
                status.markdown("**✅ Avaliação concluída!**")
                clock.markdown(
                    f"<div class='small-muted'>⏱️ Tempo total: <b>{human_time(time.time()-started)}</b></div>",
                    unsafe_allow_html=True,
                )

                st.session_state["last_processed_files"] = [arquivo_gerado] if arquivo_gerado else []
                st.session_state["last_run_done"] = True

                # Mostra resultado (preferindo arquivo_gerado, senão pega o último do Excel)
                show_result_after_run(prefer_file=arquivo_gerado)

            finally:
                # restaura TXT do projeto
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass

                # limpa pasta temporária do wav
                try:
                    shutil.rmtree(run_dir, ignore_errors=True)
                except Exception:
                    pass

# Se não for "single", a PARTE 3 cuida do resto (Visão Gerencial + Resultado geral)
# ===============================================
# FIM DA PARTE 2/3
# ===============================================

# ===============================================
# PARTE 3/3 — VISÃO GERENCIAL (até 10) + RESULTADO FINAL
# ===============================================

# ==============================
# TELA: VISÃO GERENCIAL (até 10)
# ==============================
else:
    st.markdown("### 📊 SPIN – Visão Gerencial")
    st.markdown(
        "<div class='small-muted'>Envie até <b>10</b> ligações (TXT ou WAV). "
        "O painel retorna a <b>avaliação completa por ligação</b> e também a <b>pontuação total do lote</b>.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    tipo_lote = st.selectbox(
        "Tipo de entrada",
        ["TXT (arquivos .txt ou colar vários)", "WAV (áudios .wav — recomendado servidor)"],
        index=0,
        key="tipo_lote",
    )

    vps_disponivel = bool(get_transcribe_vps_url()) and bool(get_analyze_vps_url()) and (requests is not None)

    # ==========================
    # LOTE TXT
    # ==========================
    if tipo_lote.startswith("TXT"):
        up_txts = st.file_uploader(
            "Envie até 10 arquivos .txt",
            type=["txt"],
            accept_multiple_files=True,
            key="uploader_txt_batch",
        )

        st.markdown(
            "<div class='small-muted'>Ou cole vários blocos separados por uma linha contendo <b>---</b></div>",
            unsafe_allow_html=True,
        )
        multi_txt = st.text_area("Cole aqui (separe com ---)", height=220, value="", key="multi_txt_batch")

        usar_servidor_txt = False
        if vps_disponivel:
            usar_servidor_txt = st.toggle(
                "Usar servidor para avaliar TXT (recomendado)",
                value=True,
                key="toggle_vps_txt",
            )

        if st.button("✅ Rodar lote (TXT)", use_container_width=True, key="btn_batch_txt"):
            entradas = []

            if up_txts:
                if len(up_txts) > 10:
                    st.error("Limite: 10 arquivos por lote.")
                    st.stop()
                for f in up_txts:
                    content = f.getvalue().decode("utf-8", errors="ignore")
                    entradas.append((f.name, content))

            if multi_txt.strip():
                blocos = [b.strip() for b in multi_txt.split("\n---\n") if b.strip()]
                if len(blocos) > 10:
                    st.error("Limite: 10 blocos por lote.")
                    st.stop()
                for i, b in enumerate(blocos, start=1):
                    entradas.append((f"colado_{i}.txt", b))

            if not entradas:
                st.error("Envie TXT(s) ou cole pelo menos um bloco.")
                st.stop()

            # Validar todos
            erros = []
            for name, txt in entradas:
                ok, msg = validar_txt(txt)
                if not ok:
                    erros.append((name, msg))
            if erros:
                st.error("Alguns itens estão inválidos:")
                for name, msg in erros:
                    st.write(f"- **{name}**: {msg}")
                st.stop()

            # Se for local, precisa scripts
            if not usar_servidor_txt:
                require_local_scripts_for_analysis()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=3)

            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            arquivos_criados = []
            arquivos_processados = []

            try:
                progresso_update(bar, status, clock, 1, 3, "Preparando entradas…", started)

                # Cria arquivos no TXT_DIR (mantém compatibilidade com Excel e histórico)
                for idx, (name, txt) in enumerate(entradas, start=1):
                    safe_stem = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", Path(name).stem)
                    fname = f"{batch_id}_{idx:02d}_{safe_stem}.txt"
                    (TXT_DIR / fname).write_text(txt.strip() + "\n", encoding="utf-8")
                    arquivos_criados.append(fname)

                progresso_update(bar, status, clock, 2, 3, "Avaliando o lote…", started)

                if usar_servidor_txt:
                    # Avalia 1 a 1 no servidor (cada ligação vira um item no Excel)
                    for fname in arquivos_criados:
                        text_labeled = (TXT_DIR / fname).read_text(encoding="utf-8", errors="ignore")
                        try:
                            resp = analyze_vps_text(text_labeled, filename=fname)
                            if resp.get("ok"):
                                arquivos_processados.append(str(resp.get("arquivo", fname)))
                            else:
                                arquivos_processados.append(fname)
                        except Exception:
                            arquivos_processados.append(fname)
                else:
                    # Local: roda 02 e 03 uma vez para o lote
                    rc2, _ = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=7200)
                    if rc2 != 0:
                        st.error("Não foi possível avaliar o lote no modo local.")
                        st.stop()

                    rc3, _ = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=7200)
                    if rc3 != 0:
                        st.error("Não foi possível finalizar a nota do lote no modo local.")
                        st.stop()

                    arquivos_processados = list(arquivos_criados)

                progresso_update(bar, status, clock, 3, 3, "Carregando resultados…", started)

                df = get_df_resultados()
                if df is None or df.empty:
                    st.warning("Processou, mas ainda não há resultados para exibir.")
                    st.stop()

                df_lote = filtrar_df_por_arquivos(df, arquivos_processados) if arquivos_processados else df.copy()
                if df_lote is None or df_lote.empty:
                    st.warning("Não encontrei os arquivos do lote no Excel.")
                    st.stop()

                st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

                st.markdown("### ✅ Resultados do Lote (Excel)")
                st.dataframe(df_lote, use_container_width=True)

                # Pontuação total do lote
                if "arquivo" in df_lote.columns:
                    files = sorted(df_lote["arquivo"].astype(str).unique().tolist())
                else:
                    files = []

                if files:
                    rows_map = {}
                    soma_score = 0
                    total_ligacoes = len(files)
                    max_total = 25 * total_ligacoes

                    for fname in files:
                        row = pick_row_by_file(df_lote, fname)
                        if row is not None:
                            ps = build_phase_scores_from_row(row)
                            soma_score += score_total_25(ps)
                            rows_map[fname] = row

                    # qualidade média aproximada do lote
                    media_por_ligacao = int(round(soma_score / max(total_ligacoes, 1)))
                    qualidade_label, qualidade_tag = label_qualidade_por_score25(media_por_ligacao)

                    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
                    st.markdown(
                        f"""
<div class="card">
  <div class="card-title">📌 Visão geral do lote</div>
  <div class="pill-row">
    <span class="pill"><span class="k">Ligações</span> <span class="v">{total_ligacoes}</span></span>
    <span class="pill"><span class="k">Pontuação total</span> <span class="v">{soma_score}/{max_total}</span></span>
    <span class="tag {qualidade_tag}">{qualidade_label}</span>
  </div>
  <div class="lead">Abaixo está a avaliação completa de cada ligação (Abertura + SPIN).</div>
</div>
""",
                        unsafe_allow_html=True,
                    )

                    st.markdown("### 🧾 Avaliação completa por ligação")
                    for fname in files:
                        if fname in rows_map:
                            render_avaliacao_completa(fname, rows_map[fname])

                    st.session_state["last_processed_files"] = files
                    st.session_state["last_run_done"] = True
                else:
                    st.info("Resultados carregados, mas não foi possível montar o detalhamento por item (sem coluna 'arquivo').")

            finally:
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass

    # ==========================
    # LOTE WAV
    # ==========================
    else:
        st.markdown(
            "<div class='small-muted'>No lote WAV, o modo servidor é o mais recomendado (transcrição + avaliação no servidor).</div>",
            unsafe_allow_html=True,
        )
        up_wavs = st.file_uploader(
            "Envie até 10 WAVs",
            type=["wav"],
            accept_multiple_files=True,
            key="uploader_wav_batch",
        )

        fonte_lote = st.selectbox(
            "Fonte da transcrição (lote)",
            ["Servidor (recomendado)"] if vps_disponivel else ["Local (seu 01_transcricao.py)"],
            index=0,
            key="fonte_transcricao_batch",
        )

        model_choice = st.selectbox(
            "Qualidade da transcrição (LOCAL)",
            ["small", "base", "medium"],
            index=0,
            key="model_choice_batch",
        )
        diar = st.checkbox("Tentar diarização (LOCAL)", value=True, key="diarize_batch")

        if st.button("✅ Rodar lote (WAV)", use_container_width=True, key="btn_batch_wav"):
            if not up_wavs:
                st.error("Envie pelo menos 1 WAV.")
                st.stop()
            if len(up_wavs) > 10:
                st.error("Limite: 10 WAVs por lote.")
                st.stop()

            usando_servidor = fonte_lote.startswith("Servidor")

            if not usando_servidor:
                require_local_scripts_for_analysis()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=4)

            batch_id = f"batchwav_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            arquivos_processados = []

            try:
                progresso_update(bar, status, clock, 1, 4, "Transcrevendo áudios…", started)

                for idx, wavf in enumerate(up_wavs, start=1):
                    wav_bytes = wavf.getbuffer().tobytes()

                    # valida duração (aviso)
                    try:
                        tmp_dir = UPLOADS_WAV_DIR / f"run_{batch_id}_{idx:02d}"
                        tmp_dir.mkdir(parents=True, exist_ok=True)
                        tmp_wav = tmp_dir / "audio.wav"
                        tmp_wav.write_bytes(wav_bytes)
                        dur = wav_duracao_seg(tmp_wav)
                        if dur > 600:
                            st.warning(f"⚠️ {wavf.name} tem {dur/60:.1f} min (limite recomendado 10).")
                    except Exception:
                        pass

                    if usando_servidor:
                        data_vps = transcribe_vps_wav_to_labeled_text(wav_bytes, filename=wavf.name)
                        text_labeled = (data_vps.get("text_labeled") or "").strip()
                        if not text_labeled:
                            st.error(f"A transcrição veio vazia para {wavf.name}.")
                            st.stop()

                        # salva TXT rotulado para histórico + Excel
                        fname_path = save_transcription_to_txt_dir(text_labeled, prefix=f"{batch_id}_{idx:02d}")
                        txt_name = fname_path.name

                        progresso_update(bar, status, clock, 2, 4, "Avaliando no servidor…", started)

                        resp = analyze_vps_text(text_labeled, filename=txt_name)
                        if resp.get("ok"):
                            arquivos_processados.append(str(resp.get("arquivo", txt_name)))
                        else:
                            arquivos_processados.append(txt_name)

                    else:
                        # LOCAL
                        if PY_TRANSCRIBE is None or not Path(PY_TRANSCRIBE).exists():
                            st.error("Modo local não configurado. Configure o Python da transcrição na lateral.")
                            st.stop()
                        if not SCRIPT_01.exists():
                            st.error("Módulo de transcrição local não encontrado.")
                            st.stop()

                        run_dir = UPLOADS_WAV_DIR / f"run_{batch_id}_{idx:02d}"
                        run_dir.mkdir(parents=True, exist_ok=True)
                        (run_dir / "audio.wav").write_bytes(wav_bytes)

                        rc1, out1, _ = transcribe_with_fallback(Path(PY_TRANSCRIBE), run_dir, model_choice, diar)
                        if rc1 != 0:
                            if is_oom_mkl(out1):
                                st.error("Falta de memória ao transcrever localmente. Use small ou áudios menores.")
                            else:
                                st.error(f"Não foi possível transcrever {wavf.name} no modo local.")
                            st.stop()

                if not usando_servidor:
                    progresso_update(bar, status, clock, 2, 4, "Analisando SPIN (modo local)…", started)
                    rc2, _ = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=7200)
                    if rc2 != 0:
                        st.error("Não foi possível avaliar o lote no modo local.")
                        st.stop()

                    progresso_update(bar, status, clock, 3, 4, "Finalizando nota (modo local)…", started)
                    rc3, _ = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=7200)
                    if rc3 != 0:
                        st.error("Não foi possível finalizar a nota do lote no modo local.")
                        st.stop()

                progresso_update(bar, status, clock, 4, 4, "Carregando resultados…", started)

                df = get_df_resultados()
                if df is None or df.empty:
                    st.warning("Processou, mas ainda não há resultados para exibir.")
                    st.stop()

                df_lote = filtrar_df_por_arquivos(df, arquivos_processados) if arquivos_processados else df.copy()
                if df_lote is None or df_lote.empty:
                    st.warning("Não encontrei os resultados deste lote no Excel.")
                    st.stop()

                st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
                st.markdown("### ✅ Resultados do Lote (Excel)")
                st.dataframe(df_lote, use_container_width=True)

                # detalhamento por ligação
                if "arquivo" in df_lote.columns:
                    files = sorted(df_lote["arquivo"].astype(str).unique().tolist())
                else:
                    files = []

                if files:
                    rows_map = {}
                    soma_score = 0
                    total_ligacoes = len(files)
                    max_total = 25 * total_ligacoes

                    for fname in files:
                        row = pick_row_by_file(df_lote, fname)
                        if row is not None:
                            ps = build_phase_scores_from_row(row)
                            soma_score += score_total_25(ps)
                            rows_map[fname] = row

                    media_por_ligacao = int(round(soma_score / max(total_ligacoes, 1)))
                    qualidade_label, qualidade_tag = label_qualidade_por_score25(media_por_ligacao)

                    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
                    st.markdown(
                        f"""
<div class="card">
  <div class="card-title">📌 Visão geral do lote</div>
  <div class="pill-row">
    <span class="pill"><span class="k">Ligações</span> <span class="v">{total_ligacoes}</span></span>
    <span class="pill"><span class="k">Pontuação total</span> <span class="v">{soma_score}/{max_total}</span></span>
    <span class="tag {qualidade_tag}">{qualidade_label}</span>
  </div>
  <div class="lead">Abaixo está a avaliação completa de cada ligação (Abertura + SPIN).</div>
</div>
""",
                        unsafe_allow_html=True,
                    )

                    st.markdown("### 🧾 Avaliação completa por ligação")
                    for fname in files:
                        if fname in rows_map:
                            render_avaliacao_completa(fname, rows_map[fname])

                    st.session_state["last_processed_files"] = files
                    st.session_state["last_run_done"] = True
                else:
                    st.info("Resultados carregados. (Sem coluna 'arquivo' para detalhar por item.)")

            finally:
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass


# ==============================
# RESULTADO FINAL (sempre disponível)
# ==============================
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.markdown("## 📊 Resultado")

df = get_df_resultados()
if df is None or df.empty:
    st.info("Ainda não há resultados para mostrar. Faça uma avaliação acima.")
else:
    if "arquivo" not in df.columns or df["arquivo"].astype(str).nunique() == 0:
        st.info("Resultados disponíveis, mas não há coluna 'arquivo' para seleção detalhada.")
    else:
        # tenta destacar o último processado
        last_files = st.session_state.get("last_processed_files", []) or []
        arquivos_disponiveis = sorted(df["arquivo"].astype(str).unique().tolist())

        default_idx = 0
        if last_files:
            try:
                default_idx = arquivos_disponiveis.index(str(last_files[0]))
            except Exception:
                default_idx = 0

        arquivo_foco = st.selectbox("Selecione uma ligação", arquivos_disponiveis, index=default_idx, key="select_result_file")
        row = pick_row_by_file(df, arquivo_foco)
        if row is None:
            st.info("Não encontrei os dados dessa ligação no Excel.")
        else:
            render_avaliacao_completa(str(arquivo_foco), row)


# ==============================
# Rodapé
# ==============================
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.markdown(
    "<div class='small-muted' style='text-align:center;'>SPIN Analyzer — Projeto Tele_IA 2025 | Desenvolvido por Paulo Coutinho</div>",
    unsafe_allow_html=True,
)

# ===============================================
# FIM DA PARTE 3/3
# ===============================================
