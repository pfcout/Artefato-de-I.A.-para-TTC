# ===============================================
# 🎧 SPIN Analyzer — Painel Acadêmico (TXT ou Áudio)
# ✅ 2 modos no MESMO painel:
#    1) Análise Individual (1 ligação / 1 TXT)
#    2) Análise em Lote (até 10 ligações/TXT) — “segundo painel” acessado por botão
# ✅ Mantém 100% o funcionamento LOCAL (venvs + 01_transcricao.py) como já está
# ✅ Adiciona opção VPS (API rápida) para transcrição WAV sem quebrar local
# ✅ Entregáveis do mestrado: baixar WAV/TXT/JSON (quando usa VPS)
# ✅ Reaproveita tudo (TXT_DIR + scripts 02/03 + Excel final)
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

# requests opcional (só necessário para modo VPS)
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
# 🧠 Seleção de Python por etapa
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
# 🔧 Execução segura
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
    except Exception as e:
        return 1, f"Falha ao executar o processamento: {e}"


def wav_duracao_seg(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate <= 0:
            return 0.0
        return frames / float(rate)

# ==============================
# 🌐 01 via VPS (API) — opcional e seguro
# ==============================
def get_transcribe_vps_url() -> str:
    url = os.getenv("TRANSCRIBE_API_URL", "").strip()
    try:
        if not url and hasattr(st, "secrets"):
            url = str(st.secrets.get("TRANSCRIBE_API_URL", "")).strip()
    except Exception:
        pass
    return url


def transcribe_vps_wav_to_labeled_text(wav_bytes: bytes, filename: str = "audio.wav") -> dict:
    if requests is None:
        raise RuntimeError("Dependência 'requests' não instalada. Adicione no requirements.txt.")
    url = get_transcribe_vps_url()
    if not url:
        raise RuntimeError("TRANSCRIBE_API_URL não configurado (VPS).")

    files = {"file": (filename, wav_bytes, "audio/wav")}
    r = requests.post(url, files=files, timeout=600)
    r.raise_for_status()
    return r.json()


def save_transcription_to_txt_dir(text_labeled: str, prefix: str) -> Path:
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    out_path = TXT_DIR / fname
    out_path.write_text(text_labeled.strip() + "\n", encoding="utf-8")
    return out_path


# ==============================
# 🔒 Isolamento
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
    """Remove a pasta de backup APENAS se ela estiver vazia."""
    try:
        if backup_path and backup_path.exists():
            has_any = any(backup_path.iterdir())
            if not has_any:
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
# 🧩 Mensagens programadas
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
            "com pouco controle de agenda e pouco diagnóstico consultivo. Próximo passo: estruturar a sequência "
            "Abertura → Situação → Problema → Implicação → Necessidade-benefício."
        )
    if score25 <= 12:
        return (
            "Há sinais iniciais de estrutura consultiva, mas a execução é irregular. "
            "O diagnóstico aparece em partes, com falta de follow-ups e pouca consolidação de impacto e valor."
        )
    if score25 <= 18:
        return (
            "Boa base de execução. A conversa tem direção e diagnóstico, mas ainda pode elevar consistência "
            "com quantificação (métricas), exploração de consequências e fechamento em critérios de sucesso."
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
    # (mesma lógica do seu painel original — mantive)
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
            return "Abertura bem conduzida: contexto e direção. Ajuste fino: agenda em 1 frase + confirmação do decisor/participantes."
        return "Abertura excelente: enquadramento completo (contexto, tempo, objetivo, interlocutor correto) e transição suave para diagnóstico."

    if fase == "situation":
        if nota == 0:
            return "Não houve mapeamento do cenário atual. Sem Situação, o diagnóstico fica genérico e pouco confiável."
        if nota == 1:
            return "Perguntas situacionais superficiais. Faltaram processo atual, ferramentas, responsáveis e rotina do cliente."
        if nota == 2:
            return "Você coletou o básico, mas faltaram follow-ups: volumes, frequência, exceções e critérios de controle atuais."
        if nota == 3:
            return "Boa Situação. Para elevar: quantificar e pedir exemplos recentes (métricas, tempos, volumes)."
        if nota == 4:
            return "Situação bem explorada. Ajuste fino: resumir o cenário em 1 frase e pedir confirmação do cliente."
        return "Situação excelente: processo e contexto bem mapeados, com detalhes suficientes para sustentar as próximas fases."

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
            return "Implicação pouco explorada. Faltaram consequências: custo, tempo, risco, reputação e experiência."
        if nota == 2:
            return "Você tocou no impacto, mas sem aprofundar. Sugestão: quantificar e ligar a metas do negócio."
        if nota == 3:
            return "Boa implicação. Para elevar: escolher o impacto principal e validar com o cliente."
        if nota == 4:
            return "Implicação bem construída. Ajuste fino: resumir o impacto e confirmar a leitura com o cliente."
        return "Implicação excelente: consequências claras (idealmente quantificadas) e conectadas a objetivos reais."

    if fase == "need_payoff":
        if nota == 0:
            return "Necessidade-benefício não apareceu. Sem isso, não há consolidação de valor nem critérios de sucesso."
        if nota == 1:
            return "Benefícios mencionados de forma genérica. Faltou conectar necessidades específicas a resultados desejados."
        if nota == 2:
            return "Você tentou falar de valor, mas ainda ficou pouco concreto. Sugestão: ganhos mensuráveis (tempo/custo/risco)."
        if nota == 3:
            return "Boa necessidade-benefício. Para elevar: critérios de sucesso e próximo passo com decisores."
        if nota == 4:
            return "Need-payoff bem feito. Ajuste fino: fechar com resumo de valor + compromisso de próximo passo."
        return "Need-payoff excelente: valor verbalizado, critérios claros e próximos passos bem alinhados."

    return "Feedback indisponível para esta fase."


def extracao_programada(fase: str, nota: int) -> str:
    # (mesma lógica do seu painel original — mantive)
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
        return "Extração excelente: contexto, agenda, tempo, interlocutor correto e transição para diagnóstico muito clara."

    if fase == "situation":
        if nota == 0:
            return "Não foram coletados dados do cenário atual (processo, ferramenta, rotina, responsáveis)."
        if nota == 1:
            return "Dados mínimos: faltaram processo, volumes, frequência e responsáveis."
        if nota == 2:
            return "Alguns dados do cenário surgem, mas faltam métricas e critérios (volume/tempo, exceções, regras)."
        if nota == 3:
            return "Dados relevantes coletados. Para fortalecer: números (volume/tempo) e exemplos recentes."
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
            return "Impacto foi pouco explorado: faltaram consequências e quem é afetado."
        if nota == 2:
            return "Algum impacto apareceu, mas sem quantificação (quanto custa, quantas vezes, qual risco)."
        if nota == 3:
            return "Boa extração de impacto. Para elevar: números/estimativas e ligação com metas do negócio."
        if nota == 4:
            return "Extração muito boa. Ajuste: priorizar o impacto principal e validar com o cliente."
        return "Extração excelente: impactos claros, coerentes e, quando possível, quantificados."

    if fase == "need_payoff":
        if nota == 0:
            return "Não foram coletados critérios de sucesso nem benefícios desejados (o que seria 'vitória' para o cliente)."
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
# ✅ Tratamento do erro de memória do WhisperX (mkl_malloc)
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
# 🧭 “Segundo painel” interno
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
# Sidebar: navegação + config local
# ==============================
with st.sidebar:
    st.markdown("### 🧭 Navegação")
    c1, c2 = st.columns(2)
    with c1:
        st.button("👤 Individual", use_container_width=True, on_click=go_single)
    with c2:
        st.button("📦 Lote (até 10)", use_container_width=True, on_click=go_batch)

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    with st.expander("⚙️ Configuração do Áudio (LOCAL)", expanded=False):
        st.markdown(
            "<div class='small-muted'>Se o áudio falhar por ambiente da transcrição, "
            "você pode informar manualmente o Python do ambiente <b>.venv_transcricao</b>.</div>",
            unsafe_allow_html=True,
        )
        manual_py01 = st.text_input(
            "Python do ambiente de transcrição (opcional)",
            value=st.session_state.get("manual_py01", ""),
            placeholder=r"Ex: C:\Projeto...\ .venv_transcricao\Scripts\python.exe",
            key="manual_py01_input",
        )
        if manual_py01.strip():
            st.session_state["manual_py01"] = manual_py01.strip()

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.markdown("### 🌐 VPS (opcional)")

    vps_url = get_transcribe_vps_url()
    if vps_url and requests is not None:
        st.success("VPS configurado ✅")
        st.code(vps_url)
    elif vps_url and requests is None:
        st.warning("VPS configurado, mas falta 'requests' no requirements.txt")
    else:
        st.info("VPS não configurado (ok para modo local).")
        st.markdown("<div class='small-muted'>No deploy, configure <b>TRANSCRIBE_API_URL</b> em Secrets.</div>", unsafe_allow_html=True)

# ==============================
# Detectar PY_TRANSCRIBE local (mantém igual)
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
st.markdown("## 🎧 SPIN > Análise de Ligações")
st.markdown(
    "<div class='small-muted'>Cole transcrição <b>[VENDEDOR]</b>/<b>[CLIENTE]</b> ou envie WAV. "
    "Use <b>Individual</b> para 1 ligação e <b>Lote</b> para até 10 entradas.</div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)


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

            if not SCRIPT_02.exists():
                st.error("Não foi possível localizar o módulo de análise SPIN.")
                st.stop()
            if not SCRIPT_03 or not SCRIPT_03.exists():
                st.error("Não foi possível localizar o módulo de avaliação (nota humana).")
                st.stop()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=2)

            try:
                fname = f"painel_txt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                (TXT_DIR / fname).write_text(txt_input.strip() + "\n", encoding="utf-8")

                progresso_update(bar, status, clock, 1, 2, "Analisando as fases SPIN…", started)
                rc2, out2 = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=3600)
                if rc2 != 0:
                    st.error("❌ Não foi possível analisar o texto.")
                    st.code(out2 if out2 else "(sem detalhes)")
                    st.stop()

                progresso_update(bar, status, clock, 2, 2, "Calculando a pontuação e os feedbacks…", started)
                rc3, out3 = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=3600)
                if rc3 != 0:
                    st.error("❌ Não foi possível calcular a nota final.")
                    st.code(out3 if out3 else "(sem detalhes)")
                    st.stop()

                bar.progress(1.0)
                status.markdown("**✅ Avaliação concluída!**")
                clock.markdown(
                    f"<div class='small-muted'>⏱️ Tempo total: <b>{human_time(time.time()-started)}</b></div>",
                    unsafe_allow_html=True,
                )

                st.session_state["last_run_done"] = True
                st.rerun()

            finally:
                try:
                    for f in TXT_DIR.glob("painel_txt_*.txt"):
                        try:
                            f.unlink()
                        except Exception:
                            pass
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass

    # ---------- WAV ----------
    with tab_wav:
        st.markdown("### 🎧 Avaliar a partir de um áudio (WAV)")
        st.markdown(
            "<div class='small-muted'>Envie um WAV de até 10 minutos. "
            "No deploy, o recomendado é usar VPS.</div>",
            unsafe_allow_html=True,
        )

        up_wav = st.file_uploader("Arquivo WAV", type=["wav"], key="uploader_wav_single")

        vps_url = get_transcribe_vps_url()
        vps_disponivel = bool(vps_url) and (requests is not None)

        fonte_transcricao = st.selectbox(
            "Fonte da transcrição",
            ["Local (seu 01_transcricao.py)", "VPS (API rápida)"] if vps_disponivel else ["Local (seu 01_transcricao.py)"],
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

        if fonte_transcricao.startswith("VPS"):
            st.info(f"🌐 VPS: {vps_url}")

        if st.button("✅ Avaliar áudio", use_container_width=True, key="btn_wav_single"):
            if up_wav is None:
                st.error("Envie um arquivo WAV para continuar.")
                st.stop()

            if not SCRIPT_02.exists():
                st.error("Não foi possível localizar o módulo de análise SPIN.")
                st.stop()
            if not SCRIPT_03 or not SCRIPT_03.exists():
                st.error("Não foi possível localizar o módulo de avaliação (nota humana).")
                st.stop()

            run_dir = UPLOADS_WAV_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_dir.mkdir(parents=True, exist_ok=True)
            wav_path = run_dir / "audio.wav"
            wav_path.write_bytes(up_wav.getbuffer())

            try:
                dur = wav_duracao_seg(wav_path)
            except Exception:
                dur = 0.0

            if dur > 600:
                st.error(f"⛔ O áudio tem {dur/60:.1f} minutos. O limite é 10 minutos.")
                st.stop()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=3)

            try:
                progresso_update(bar, status, clock, 1, 3, "Transcrevendo o áudio…", started)

                # ===== VPS =====
                if fonte_transcricao.startswith("VPS"):
                    try:
                        wav_bytes = up_wav.getbuffer().tobytes()
                        data_vps = transcribe_vps_wav_to_labeled_text(wav_bytes, filename=up_wav.name)
                        text_labeled = data_vps.get("text_labeled", "").strip()

                        if not text_labeled:
                            st.error("❌ A transcrição do VPS veio vazia.")
                            st.stop()

                        out_txt_path = save_transcription_to_txt_dir(text_labeled, prefix="painel_wav_vps")

                        # Entregáveis do mestrado
                        st.download_button("📥 Baixar WAV", data=wav_bytes, file_name=up_wav.name)
                        st.download_button("📥 Baixar TXT (rotulado)", data=text_labeled, file_name="transcricao_rotulada.txt")
                        st.download_button(
                            "📥 Baixar JSON (VPS)",
                            data=json.dumps(data_vps, ensure_ascii=False, indent=2),
                            file_name="transcricao_vps.json",
                        )

                        st.success(f"✅ TXT criado: {out_txt_path.name}")

                    except Exception as e:
                        st.error("❌ Não foi possível transcrever via VPS.")
                        st.code(str(e))
                        st.stop()

                # ===== LOCAL =====
                else:
                    if PY_TRANSCRIBE is None or not Path(PY_TRANSCRIBE).exists():
                        st.error(
                            "Não foi possível acessar o ambiente de transcrição do áudio.\n\n"
                            "Abra a seção 'Configuração do Áudio' na lateral e informe o Python do ambiente .venv_transcricao."
                        )
                        st.stop()

                    if not SCRIPT_01.exists():
                        st.error("Não foi possível localizar o módulo de transcrição do áudio.")
                        st.stop()

                    rc1, out1, model_used = transcribe_with_fallback(Path(PY_TRANSCRIBE), run_dir, model_choice, diar)
                    if rc1 != 0:
                        if is_oom_mkl(out1):
                            st.error(
                                "❌ Falta de memória ao transcrever no Windows.\n\n"
                                "✅ Use o modelo **small** ou envie um áudio menor."
                            )
                        else:
                            st.error("❌ Não foi possível transcrever o áudio.")
                        st.code(out1 if out1 else "(sem detalhes)")
                        st.stop()

                progresso_update(bar, status, clock, 2, 3, "Analisando as fases SPIN…", started)
                rc2, out2 = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=7200)
                if rc2 != 0:
                    st.error("❌ Não foi possível analisar a conversa transcrita.")
                    st.code(out2 if out2 else "(sem detalhes)")
                    st.stop()

                progresso_update(bar, status, clock, 3, 3, "Calculando a pontuação e os feedbacks…", started)
                rc3, out3 = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=7200)
                if rc3 != 0:
                    st.error("❌ Não foi possível calcular a nota final.")
                    st.code(out3 if out3 else "(sem detalhes)")
                    st.stop()

                bar.progress(1.0)
                status.markdown("**✅ Avaliação concluída!**")
                clock.markdown(
                    f"<div class='small-muted'>⏱️ Tempo total: <b>{human_time(time.time()-started)}</b></div>",
                    unsafe_allow_html=True,
                )

                st.session_state["last_run_done"] = True
                st.rerun()

            finally:
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass
                try:
                    shutil.rmtree(run_dir, ignore_errors=True)
                except Exception:
                    pass


# ==============================
# TELA: LOTE (até 10)
# ==============================
else:
    st.markdown("### 📦 Painel em Lote (até 10)")
    st.markdown(
        "<div class='small-muted'>Envie até 10 entradas. "
        "O sistema processa tudo e retorna a nota de cada item.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

    tipo_lote = st.selectbox(
        "Tipo de entrada",
        ["TXT (arquivos .txt ou colar vários)", "WAV (áudios .wav — recomendado VPS)"],
        index=0,
        key="tipo_lote",
    )

    vps_url = get_transcribe_vps_url()
    vps_disponivel = bool(vps_url) and (requests is not None)

    if tipo_lote.startswith("TXT"):
        up_txts = st.file_uploader("Envie até 10 arquivos .txt", type=["txt"], accept_multiple_files=True, key="uploader_txt_batch")
        st.markdown("<div class='small-muted'>Ou cole vários blocos separados por uma linha com <b>---</b></div>", unsafe_allow_html=True)
        multi_txt = st.text_area("Cole aqui (separe com ---)", height=220, value="", key="multi_txt_batch")

        if st.button("✅ Rodar lote (TXT)", use_container_width=True, key="btn_batch_txt"):
            if not SCRIPT_02.exists():
                st.error("Não foi possível localizar o módulo de análise SPIN.")
                st.stop()
            if not SCRIPT_03 or not SCRIPT_03.exists():
                st.error("Não foi possível localizar o módulo de avaliação (nota humana).")
                st.stop()

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

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=2)

            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            arquivos_criados = []

            try:
                # cria arquivos do lote
                for idx, (name, txt) in enumerate(entradas, start=1):
                    safe_stem = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", Path(name).stem)
                    fname = f"{batch_id}_{idx:02d}_{safe_stem}.txt"
                    (TXT_DIR / fname).write_text(txt.strip() + "\n", encoding="utf-8")
                    arquivos_criados.append(fname)

                progresso_update(bar, status, clock, 1, 2, "Analisando SPIN (02)…", started)
                rc2, out2 = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=7200)
                if rc2 != 0:
                    st.error("❌ Falha no 02 (SPIN).")
                    st.code(out2 if out2 else "(sem detalhes)")
                    st.stop()

                progresso_update(bar, status, clock, 2, 2, "Calculando nota final (03)…", started)
                rc3, out3 = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=7200)
                if rc3 != 0:
                    st.error("❌ Falha no 03 (nota).")
                    st.code(out3 if out3 else "(sem detalhes)")
                    st.stop()

                bar.progress(1.0)
                status.markdown("**✅ Lote concluído!**")
                clock.markdown(
                    f"<div class='small-muted'>⏱️ Tempo total: <b>{human_time(time.time()-started)}</b></div>",
                    unsafe_allow_html=True,
                )

                df = get_df_resultados()
                if df is None or df.empty:
                    st.warning("Processou, mas ainda não há Excel para exibir.")
                else:
                    df_lote = filtrar_df_por_arquivos(df, arquivos_criados)
                    if df_lote.empty:
                        st.warning("Não encontrei os arquivos do lote no Excel. (Vamos ajustar no 02/03 depois, se necessário.)")
                    else:
                        st.markdown("### ✅ Resultados do Lote")
                        st.dataframe(df_lote, use_container_width=True)

                st.success("✅ Você pode rodar outro lote agora, sem afetar o histórico do Excel.")

            finally:
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass

    else:
        # WAV lote
        st.markdown("<div class='small-muted'>Para lote WAV no deploy, o recomendado é VPS.</div>", unsafe_allow_html=True)
        up_wavs = st.file_uploader("Envie até 10 WAVs", type=["wav"], accept_multiple_files=True, key="uploader_wav_batch")

        fonte_lote = st.selectbox(
            "Fonte da transcrição (lote)",
            ["VPS (recomendado)"] if vps_disponivel else ["Local (seu 01_transcricao.py)"],
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

        if fonte_lote.startswith("VPS"):
            st.info(f"🌐 VPS: {vps_url}")

        if st.button("✅ Rodar lote (WAV)", use_container_width=True, key="btn_batch_wav"):
            if not up_wavs:
                st.error("Envie pelo menos 1 WAV.")
                st.stop()
            if len(up_wavs) > 10:
                st.error("Limite: 10 WAVs por lote.")
                st.stop()

            if not SCRIPT_02.exists():
                st.error("Não foi possível localizar o módulo de análise SPIN.")
                st.stop()
            if not SCRIPT_03 or not SCRIPT_03.exists():
                st.error("Não foi possível localizar o módulo de avaliação (nota humana).")
                st.stop()

            backup_path = backup_txts_existentes()
            started = time.time()
            bar, status, clock = progresso(total_steps=3)

            batch_id = f"batchwav_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            arquivos_criados = []

            try:
                progresso_update(bar, status, clock, 1, 3, "Transcrevendo WAVs…", started)

                for idx, wavf in enumerate(up_wavs, start=1):
                    wav_bytes = wavf.getbuffer().tobytes()

                    # checar duração só para aviso (não aborta em lote por padrão)
                    # (se quiser abortar, eu coloco)
                    try:
                        run_dir = UPLOADS_WAV_DIR / f"run_{batch_id}_{idx:02d}"
                        run_dir.mkdir(parents=True, exist_ok=True)
                        tmp_wav = run_dir / "audio.wav"
                        tmp_wav.write_bytes(wav_bytes)
                        dur = wav_duracao_seg(tmp_wav)
                        if dur > 600:
                            st.warning(f"⚠️ {wavf.name} tem {dur/60:.1f} min (limite recomendado 10).")
                    except Exception:
                        pass

                    if fonte_lote.startswith("VPS"):
                        data_vps = transcribe_vps_wav_to_labeled_text(wav_bytes, filename=wavf.name)
                        text_labeled = data_vps.get("text_labeled", "").strip()
                        if not text_labeled:
                            st.error(f"❌ VPS retornou vazio em {wavf.name}.")
                            st.stop()
                        fname = save_transcription_to_txt_dir(text_labeled, prefix=f"{batch_id}_{idx:02d}")
                        arquivos_criados.append(fname.name)
                    else:
                        # LOCAL
                        if PY_TRANSCRIBE is None or not Path(PY_TRANSCRIBE).exists():
                            st.error("PY_TRANSCRIBE não encontrado. Configure o Python da transcrição na sidebar.")
                            st.stop()
                        if not SCRIPT_01.exists():
                            st.error("01_transcricao.py não encontrado.")
                            st.stop()

                        run_dir = UPLOADS_WAV_DIR / f"run_{batch_id}_{idx:02d}"
                        run_dir.mkdir(parents=True, exist_ok=True)
                        (run_dir / "audio.wav").write_bytes(wav_bytes)

                        rc1, out1, _ = transcribe_with_fallback(Path(PY_TRANSCRIBE), run_dir, model_choice, diar)
                        if rc1 != 0:
                            st.error(f"❌ Falha ao transcrever localmente: {wavf.name}")
                            st.code(out1 if out1 else "(sem detalhes)")
                            st.stop()

                        # o 01 local já cria TXT_DIR, então a gente coleta os txts novos depois
                        # (vamos ajustar isso quando você mandar o 01/02/03, se necessário)

                progresso_update(bar, status, clock, 2, 3, "Analisando SPIN (02)…", started)
                rc2, out2 = run_cmd(PY_ZEROSHOT, SCRIPT_02, [], ROOT_DIR, timeout_s=7200)
                if rc2 != 0:
                    st.error("❌ Falha no 02 (SPIN).")
                    st.code(out2 if out2 else "(sem detalhes)")
                    st.stop()

                progresso_update(bar, status, clock, 3, 3, "Calculando nota final (03)…", started)
                rc3, out3 = run_cmd(PY_ZEROSHOT, SCRIPT_03, [], ROOT_DIR, timeout_s=7200)
                if rc3 != 0:
                    st.error("❌ Falha no 03 (nota).")
                    st.code(out3 if out3 else "(sem detalhes)")
                    st.stop()

                df = get_df_resultados()
                if df is None or df.empty:
                    st.warning("Processou, mas ainda não há Excel para exibir.")
                else:
                    df_lote = filtrar_df_por_arquivos(df, arquivos_criados) if arquivos_criados else df
                    st.markdown("### ✅ Resultados do Lote (WAV)")
                    st.dataframe(df_lote, use_container_width=True)

            finally:
                try:
                    restore_txts(backup_path)
                    cleanup_backup_dir(backup_path)
                except Exception:
                    pass


# ==============================
# ✅ Resultado Individual (mantém sua lógica)
# ==============================
st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.markdown("## 📊 Resultado")

df = carregar_resultado_final()
if df is None or df.empty:
    st.info("Ainda não há resultados para mostrar. Faça uma avaliação acima.")
    st.stop()

df = normalizar_df(df)
ultima = df.iloc[-1]

phase_scores = {
    "abertura": clamp_int(ultima.get("abertura_nota_humana", 0), 0, 5),
    "situation": clamp_int(ultima.get("situation_nota_humana", 0), 0, 5),
    "problem": clamp_int(ultima.get("problem_nota_humana", 0), 0, 5),
    "implication": clamp_int(ultima.get("implication_nota_humana", 0), 0, 5),
    "need_payoff": clamp_int(ultima.get("need_payoff_nota_humana", 0), 0, 5),
}

score25 = score_total_25(phase_scores)
qualidade_label, qualidade_tag = label_qualidade_por_score25(score25)
msg_geral = msg_geral_por_score25(score25)

arquivo = str(ultima.get("arquivo", "—"))
processado_em = str(ultima.get("processado_em", ultima.get("avaliado_em", "—")))

st.markdown(f"<span class='badge'>Avaliação carregada</span>", unsafe_allow_html=True)
st.markdown("")

c1, c2, c3 = st.columns([1.2, 1.6, 1.6])
with c1:
    st.markdown(
        f"<div class='metric'><div class='label'>Pontuação Total (Abertura + SPIN)</div><div class='value'>{score25}/25</div></div>",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"<div class='metric'><div class='label'>Arquivo</div><div class='value' style='font-size:1.2rem'>{arquivo}</div></div>",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"<div class='metric'><div class='label'>Data/Hora</div><div class='value' style='font-size:1.15rem'>{processado_em}</div></div>",
        unsafe_allow_html=True,
    )

st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

st.markdown("### ✅ Avaliação geral")
st.markdown(
    f"""
<div class="card">
  <div class="card-title">Resumo executivo</div>
  <div class="pill-row">
    <span class="pill"><span class="k">Pontuação Total</span> <span class="v">{score25}/25</span></span>
    <span class="tag {qualidade_tag}">{qualidade_label}</span>
  </div>
  <div class="lead">{msg_geral}</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 📌 Critérios (Abertura + SPIN)")

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

    st.markdown(
        f"""
<div class="card">
  <div class="card-title">{label}</div>

  <div class="pill-row">
    <span class="pill"><span class="k">Nota</span> <span class="v">{nota}/5</span></span>
    <span class="pill"><span class="k">Ranking</span> <span class="v">{rank}</span></span>
    <span class="tag {tc}">{ "Excelente" if nota==5 else ("Bom" if nota==4 else ("Intermediário" if nota==3 else ("Iniciante" if nota in (1,2) else "Ausente"))) }</span>
  </div>

  <div class="grid2">
    <div class="block">
      <h4>Feedback (avaliação profissional)</h4>
      <p>{fb}</p>
    </div>
    <div class="block">
      <h4>Extração de dados (evidências)</h4>
      <p>{ex}</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
st.markdown(
    "<div class='small-muted' style='text-align:center;'>SPIN > Análise Individual (Painel Acadêmico)</div>",
    unsafe_allow_html=True,
)
