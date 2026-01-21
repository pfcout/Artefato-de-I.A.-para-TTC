# ==============================================================
# 03_avaliacao_zeroshot.py
# Projeto: Tele_IA Transcrição
# Objetivo:
#   - Ler a planilha do 02 (resultados_completos_SPIN.xlsx)
#   - Para cada fase, dar uma NOTA HUMANA (0–5) com Ollama
#   - Gerar nota_final (0–10) + classificação
# Saída: saida_avaliacao/excel/avaliacao_spin_avancada.xlsx
# ==============================================================

import sys
import os
import re
import json
import pandas as pd
from datetime import datetime
from urllib import request
from urllib.error import URLError, HTTPError

# ===========================================================
# PATH FIX
# ===========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# ===========================================================
# CONFIG OLLAMA (mesmo padrão do 02)
# ===========================================================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")

OLLAMA_OPTIONS = {
    "temperature": 0,
    "num_ctx": 2048,
    "num_predict": 64,
    "top_p": 0.9,
}
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "5m")

# ===========================================================
# CAMINHOS
# ===========================================================
ENTRADA_EXCEL = os.path.join(ROOT_DIR, "saida_excel", "resultados_completos_SPIN.xlsx")

SAIDA_EXCEL_DIR = os.path.join(ROOT_DIR, "saida_avaliacao", "excel")
os.makedirs(SAIDA_EXCEL_DIR, exist_ok=True)

SAIDA_EXCEL = os.path.join(SAIDA_EXCEL_DIR, "avaliacao_spin_avancada.xlsx")

# ===========================================================
# HELPERS: OLLAMA CALL
# ===========================================================
def ollama_generate(prompt: str, timeout_s: int = 120) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": OLLAMA_OPTIONS,
    }

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            obj = json.loads(raw)
            return (obj.get("response") or "").strip()
    except (HTTPError, URLError) as e:
        raise RuntimeError(f"Ollama API error: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}") from e

# ===========================================================
# LEITURA
# ===========================================================
df = pd.read_excel(ENTRADA_EXCEL)
print(f"📂 Planilha carregada com {len(df)} registros: {ENTRADA_EXCEL}")

# ===========================================================
# FUNÇÃO: extrair nota 0–5 com robustez
# ===========================================================
NOTA_RE = re.compile(r"\b([0-5])\b")

def extrair_nota(texto_saida: str) -> int:
    """
    Aceita qualquer saída e tenta achar um dígito 0..5.
    Se vier fora, cai em fallback.
    """
    if not texto_saida:
        return 0
    m = NOTA_RE.search(texto_saida)
    if not m:
        return 0
    n = int(m.group(1))
    if n < 0:
        return 0
    if n > 5:
        return 5
    return n

# ===========================================================
# AVALIAÇÃO HUMANA (0–5)
# ===========================================================
def avaliar_fase_humana(fase: str, texto: str) -> int:
    """
    Retorna nota 0..5.
    Regra:
      - 0 apenas se estiver vazio / não houver tentativa real.
      - 1..5 conforme qualidade.
    """
    if not isinstance(texto, str) or not texto.strip():
        return 0

    # para reduzir custo e evitar prompt gigante quando o 02 juntou falas com " | "
    # pega no máx. os primeiros 1200 chars (suficiente pra avaliar)
    texto_curto = texto.strip()
    if len(texto_curto) > 1200:
        texto_curto = texto_curto[:1200] + "..."

    prompt = f"""
Você é um avaliador humano experiente em vendas consultivas (SPIN Selling - Neil Rackham).

Tarefa:
Avalie a qualidade da fase SPIN "{fase}" no trecho abaixo (fala(s) do VENDEDOR).

Regras IMPORTANTES:
- Considere a INTENÇÃO humana, mesmo que a execução seja ruim.
- Dê nota 0 APENAS se não houver tentativa real dessa fase.
- Caso exista qualquer tentativa, dê nota entre 1 e 5.

Escala:
0 = nenhuma tentativa da fase
1 = tentativa muito fraca
2 = tentativa fraca
3 = aceitável
4 = boa
5 = excelente

Responda APENAS com UM número inteiro (0,1,2,3,4 ou 5). Nada mais.

Trecho:
\"\"\"{texto_curto}\"\"\"
"""

    try:
        out = ollama_generate(prompt, timeout_s=120)
        nota = extrair_nota(out)
        return nota
    except Exception as e:
        # fallback seguro: se tem texto, não zera (pra não punir por erro técnico)
        print(f"⚠️ Falha ao avaliar fase='{fase}': {e}")
        return 1

# ===========================================================
# AVALIAÇÃO
# ===========================================================
FASES = ["abertura", "situation", "problem", "implication", "need_payoff"]

# garante colunas (evita warning e bagunça)
for fase in FASES:
    col = f"{fase}_nota_humana"
    if col not in df.columns:
        df[col] = 0

df["nota_final"] = 0.0
df["classificacao_spin"] = ""

for idx, row in df.iterrows():
    soma = 0
    maximo = len(FASES) * 5  # 25

    for fase in FASES:
        texto = row.get(f"{fase}_texto", "")
        nota = avaliar_fase_humana(fase, texto)
        df.at[idx, f"{fase}_nota_humana"] = int(nota)
        soma += int(nota)

    df.at[idx, "nota_final"] = round((soma / maximo) * 10, 2)

# ===========================================================
# CLASSIFICAÇÃO
# ===========================================================
def classificar(nota: float) -> str:
    if nota >= 8:
        return "Excelente"
    elif nota >= 5:
        return "Intermediária"
    elif nota > 0:
        return "Inicial"
    return "Insuficiente"

df["classificacao_spin"] = df["nota_final"].apply(classificar)

# ===========================================================
# METADADOS ÚTEIS (ajuda debug e entrega)
# ===========================================================
df["avaliado_em"] = datetime.now().isoformat(timespec="seconds")
df["modelo_avaliacao"] = OLLAMA_MODEL

# ===========================================================
# EXPORTAÇÃO
# ===========================================================
df.to_excel(SAIDA_EXCEL, index=False)

print("🎯 Avaliação SPIN HUMANA concluída!")
print(f"📊 Excel salvo em: {SAIDA_EXCEL}")