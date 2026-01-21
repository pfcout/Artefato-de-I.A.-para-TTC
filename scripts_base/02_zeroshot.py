# ===========================================================
# 02_zeroshot.py (UPGRADED v2 - Precisão SPIN + Need-payoff firme + sem mistura)
# Projeto: Tele_IA Transcrição
# Objetivo: Ler arquivos .txt do 01, identificar falas do VENDEDOR com robustez
#           e classificar SPIN via Ollama (gemma2:2b), salvando Excel final.
#
# ✅ Mantém o mesmo formato do Excel (compatível com 03 e painel)
# ✅ Remove "mistura": 1 fala -> 1 fase
# ✅ Fortalece detecção de need_payoff e implication
# ===========================================================

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
# CONFIG OLLAMA
# ===========================================================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")

# Segurança: reduzir custo/memória
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
ENTRADA_DIR = os.path.join(ROOT_DIR, "arquivos_transcritos", "txt")
SAIDA_EXCEL_DIR = os.path.join(ROOT_DIR, "saida_excel")
os.makedirs(SAIDA_EXCEL_DIR, exist_ok=True)

EXCEL_PATH = os.path.join(SAIDA_EXCEL_DIR, "resultados_completos_SPIN.xlsx")

labels = ["abertura", "situation", "problem", "implication", "need_payoff"]

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
# TAGS NO TXT
# ===========================================================
TAG_RE = re.compile(r"^\s*\[(VENDEDOR|CLIENTE|SPEAKER_\d+|UNK)\]\s*", re.IGNORECASE)

def limpar_tag(linha: str):
    m = TAG_RE.match(linha)
    tag = None
    if m:
        tag = m.group(1).upper()
        linha = TAG_RE.sub("", linha).strip()
    return tag, linha.strip()

# ===========================================================
# CLASSIFICAÇÃO DE PAPEL (VENDEDOR/CLIENTE)
# ===========================================================
COMMAND_ROLE = """
Classifique a fala abaixo como sendo do VENDEDOR ou do CLIENTE.

Responda APENAS com UMA palavra:
VENDEDOR ou CLIENTE
"""

VENDEDOR_PATTERNS = [
    "aqui é", "sou da", "estou ligando", "estou entrando em contato",
    "nossa empresa", "posso falar", "falo com", "bom dia", "boa tarde", "boa noite",
    "prazer", "meu nome é", "estou te chamando", "só pra confirmar", "vou te mandar",
    "te encaminho", "posso te enviar", "me confirma", "vou confirmar",
    "deixa eu confirmar", "vou verificar", "posso te ajudar", "vou te passar",
]
CLIENTE_PATTERNS = [
    "tudo bem", "ok", "sim", "claro", "pode", "pode sim", "aham", "uhum",
    "não", "não tenho", "não posso", "quanto custa", "qual valor", "me manda",
    "me envia", "vou ver", "prefiro", "quero", "preciso", "tá bom", "beleza",
    "quanto fica", "tem como", "pode ser", "fechado",
]

def classificar_papel_regra(texto: str):
    t = texto.lower()
    if any(p in t for p in VENDEDOR_PATTERNS):
        return "VENDEDOR"
    if any(p in t for p in CLIENTE_PATTERNS):
        return "CLIENTE"
    return None

def classificar_papel_ia(texto: str) -> str:
    r = classificar_papel_regra(texto)
    if r:
        return r

    prompt = f"{COMMAND_ROLE}\n\nFALA:\n{texto}\n"
    out = ollama_generate(prompt, timeout_s=60).upper()

    if re.search(r"\bVENDEDOR\b", out):
        return "VENDEDOR"
    if re.search(r"\bCLIENTE\b", out):
        return "CLIENTE"
    return "CLIENTE"

# ===========================================================
# ✅ "parece vendedor"
# ===========================================================
def parece_vendedor(texto: str) -> bool:
    t = texto.lower().strip()
    if not t:
        return False

    if "?" in texto:
        return True

    if t.startswith(("quanto", "qual", "como", "quando", "onde", "por que", "pq", "pode", "você", "vc")):
        return True

    if any(x in t for x in [
        "pra eu entender", "para eu entender", "só pra confirmar", "me confirma",
        "vamos", "vou", "deixa eu", "entendi", "certo", "perfeito", "então",
        "me diz", "me fala", "me passa", "consegue", "poderia"
    ]):
        return True

    return False

# ===========================================================
# GUARDRAILS DE PAPEL (contexto)
# ===========================================================
def eh_curta(texto: str) -> bool:
    t = texto.strip()
    return (len(t) <= 35) or (len(t.split()) <= 4)

def eh_pergunta(texto: str) -> bool:
    t = texto.strip()
    if "?" in t:
        return True
    lower = t.lower()
    starts = ("quanto", "qual", "como", "quando", "onde", "por que", "pq", "pode", "você", "vc")
    return lower.startswith(starts)

def corrigir_papeis_com_contexto(falas):
    saida = []
    ultimo_papel = None
    streak_vendedor = 0

    for i, (tag, texto) in enumerate(falas):
        texto = (texto or "").strip()
        if not texto:
            continue

        if i == 0:
            papel = "VENDEDOR"
        else:
            if tag in ("VENDEDOR", "CLIENTE"):
                papel = tag
            else:
                papel = classificar_papel_ia(texto)

            if classificar_papel_regra(texto) == "VENDEDOR" or parece_vendedor(texto):
                papel = "VENDEDOR"

            if ultimo_papel == "VENDEDOR" and (not eh_pergunta(texto)) and eh_curta(texto):
                papel = "CLIENTE"

            if ultimo_papel == "CLIENTE" and eh_pergunta(texto):
                papel = "VENDEDOR"

            if streak_vendedor >= 2 and papel == "CLIENTE":
                if parece_vendedor(texto) or any(x in texto.lower() for x in ["vou", "vamos", "me confirma", "só pra", "entendi", "certo", "perfeito"]):
                    papel = "VENDEDOR"

        if papel == "VENDEDOR":
            streak_vendedor += 1
        else:
            streak_vendedor = 0

        ultimo_papel = papel
        saida.append((papel, texto))

    return saida

def ler_falas_txt(caminho_txt: str):
    raw = []
    with open(caminho_txt, "r", encoding="utf-8", errors="ignore") as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]

    for linha in linhas:
        tag, texto = limpar_tag(linha)
        raw.append((tag, texto))

    return corrigir_papeis_com_contexto(raw)

# ===========================================================
# SPIN — CLASSIFICAÇÃO (UMA FASE) MAIS FIRME
# ===========================================================
COMMAND_SPIN_SINGLE = """
Você é especialista em SPIN Selling (Neil Rackham).

Classifique a fala do VENDEDOR em UMA ÚNICA fase predominante.

Definições objetivas:
- abertura: cumprimento/apresentação/agenda, confirmação de contato, alinhamento de tempo e motivo do contato.
- situation: entender contexto atual (processo, ferramenta, volume, rotina, como fazem hoje).
- problem: evidenciar dor/dificuldade/falha do cenário atual.
- implication: explorar impacto/consequência/risco/custo dessa dor (o que acontece se continuar, perdas, atrasos, reputação).
- need_payoff: fazer o cliente verbalizar valor/benefício desejado ou aceitar o ganho (ex: "se eu te mostrasse...", "faria sentido se...", "isso ajudaria...").

Regras IMPORTANTES para desempate:
1) Se a frase fala de risco/impacto futuro -> implication.
2) Se a frase fala de benefício/ganho desejado, "e se...", "se eu te mostrasse..." -> need_payoff.
3) Se descreve dor atual -> problem.
4) Se descreve cenário atual -> situation.
5) Cumprimento/apresentação/agenda -> abertura.

Responda APENAS com UMA palavra (minúsculas):
abertura
situation
problem
implication
need_payoff
"""

def normalize_spin_label(out: str) -> str:
    out = (out or "").strip().lower()
    out = re.sub(r"[^a-z_]+", " ", out).strip()
    parts = out.split()
    if not parts:
        return ""
    tok = parts[0]
    if tok in labels:
        return tok
    joined = "_".join(parts[:2])
    if joined == "need_payoff":
        return "need_payoff"
    return ""

# ===========================================================
# ✅ Regras fortes (pós-correção) p/ separar implication vs need_payoff
# ===========================================================
NEED_PAYOFF_TRIGGERS = [
    "se eu te mostrasse", "se eu te apresentar", "se eu te mostrar",
    "e se", "imagina se", "faria sentido se", "faz sentido se",
    "isso ajudaria", "ajudaria", "valeria a pena", "valeria",
    "resolveria", "melhoraria", "facilitaria",
    "o ideal seria", "seria útil", "seria bom",
    "o que você gostaria", "o que vocês gostariam",
    "qual seria o cenário ideal", "qual seria o ideal",
    "se tivesse", "se vocês tivessem"
]

IMPLICATION_TRIGGERS = [
    "se continuar", "se isso continuar", "qual o risco", "quais os riscos",
    "isso pode gerar", "isso gera", "isso causa", "isso impacta",
    "qual o impacto", "qual o prejuízo", "prejuízo", "perda", "perder",
    "reputação", "faturamento", "cancelamento", "reagendamento",
    "atraso", "retrabalho", "custo", "custando", "tempo perdido",
    "pode acontecer", "pode dar", "pode levar", "vai resultar", "vai causar"
]

PROBLEM_TRIGGERS = [
    "problema", "dor", "dificuldade", "falha", "erro", "demora",
    "não funciona", "ruim", "complica", "retrabalho", "atraso", "falta",
    "quebra", "bagunça", "desorganizado", "perde", "perdendo"
]

SITUATION_TRIGGERS = [
    "hoje", "atualmente", "como vocês", "como funciona", "qual sistema",
    "vocês usam", "processo", "rotina", "no dia a dia", "quantos",
    "com que frequência", "quem", "quando", "onde", "quanto tempo"
]

ABERTURA_TRIGGERS = [
    "alô", "oi", "olá", "bom dia", "boa tarde", "boa noite",
    "aqui é", "meu nome é", "sou da", "falo com", "posso falar",
    "rapidinho", "só pra", "agenda", "tempo", "minutinhos"
]

def forced_spin_by_rules(fala: str) -> str:
    t = (fala or "").lower()

    # Need-payoff primeiro (mais específico)
    if any(x in t for x in NEED_PAYOFF_TRIGGERS):
        return "need_payoff"

    # Implication (impacto/risco) é bem característico
    if any(x in t for x in IMPLICATION_TRIGGERS):
        return "implication"

    # Problem (dor atual)
    if any(x in t for x in PROBLEM_TRIGGERS):
        return "problem"

    # Situation
    if any(x in t for x in SITUATION_TRIGGERS) or ("?" in fala):
        return "situation"

    # Abertura
    if any(x in t for x in ABERTURA_TRIGGERS):
        return "abertura"

    return ""

# ===========================================================
# ✅ Fallback por SCORE (1 fala -> 1 fase)
# ===========================================================
def spin_score(fala: str) -> dict:
    t = (fala or "").lower()

    score = {k: 0 for k in labels}

    # abertura
    for x in ABERTURA_TRIGGERS:
        if x in t:
            score["abertura"] += 2

    # situation
    for x in SITUATION_TRIGGERS:
        if x in t:
            score["situation"] += 2
    if "?" in fala:
        score["situation"] += 1

    # problem
    for x in PROBLEM_TRIGGERS:
        if x in t:
            score["problem"] += 3

    # implication
    for x in IMPLICATION_TRIGGERS:
        if x in t:
            score["implication"] += 4

    # need_payoff
    for x in NEED_PAYOFF_TRIGGERS:
        if x in t:
            score["need_payoff"] += 5

    # Heurística: frases com "se ... continuar" puxam implication
    if "se" in t and "continu" in t:
        score["implication"] += 3

    # Heurística: "se eu te mostrasse" é need_payoff fortíssimo
    if "se eu te mostrasse" in t or "se eu te mostrar" in t:
        score["need_payoff"] += 8

    return score

def spin_fallback_single(fala: str) -> str:
    # 1) regras forçadas (alta precisão)
    forced = forced_spin_by_rules(fala)
    if forced:
        return forced

    # 2) score geral
    score = spin_score(fala)

    # desempate por prioridade (impacto e valor acima de dor e contexto)
    priority = ["need_payoff", "implication", "problem", "situation", "abertura"]
    best = max(priority, key=lambda k: (score.get(k, 0), -priority.index(k)))

    # se tudo zerado, assume situation (pergunta/contexto)
    if score.get(best, 0) == 0:
        return "situation"

    return best

# ===========================================================
# CLASSIFICAÇÃO FINAL DE FASE
# ===========================================================
def classificar_spin_fase(fala: str) -> str:
    # 0) correção rápida por regras (evita erro do modelo)
    forced = forced_spin_by_rules(fala)
    if forced:
        return forced

    # 1) IA
    prompt = f"{COMMAND_SPIN_SINGLE}\n\nFALA:\n{fala}\n"
    out = ollama_generate(prompt, timeout_s=90)
    fase = normalize_spin_label(out)

    # 2) se IA não retornou válido, fallback único
    if not fase:
        fase = spin_fallback_single(fala)
        return fase

    # 3) pós-correção (casos clássicos que o modelo confunde)
    # need-payoff vs implication
    if fase != "need_payoff" and any(x in (fala.lower()) for x in NEED_PAYOFF_TRIGGERS):
        return "need_payoff"
    if fase != "implication" and any(x in (fala.lower()) for x in IMPLICATION_TRIGGERS):
        return "implication"

    return fase

# ===========================================================
# PROCESSAMENTO PRINCIPAL
# ===========================================================
def main():
    if not os.path.isdir(ENTRADA_DIR):
        print(f"⛔ Pasta de entrada não encontrada: {ENTRADA_DIR}")
        return

    arquivos_txt = [f for f in os.listdir(ENTRADA_DIR) if f.lower().endswith(".txt")]
    print("📂 Arquivos encontrados:", arquivos_txt)

    resultados_finais = []

    for arquivo in arquivos_txt:
        print(f"\n📄 Processando: {arquivo}")
        caminho = os.path.join(ENTRADA_DIR, arquivo)

        falas = ler_falas_txt(caminho)

        # não perde falas de vendedor mesmo se rotulou errado
        falas_vendedor = [t for (papel, t) in falas if papel == "VENDEDOR" or parece_vendedor(t)]

        print(f"   - Total de linhas: {len(falas)} | Vendedor(+guardrail): {len(falas_vendedor)}")
        for idx, (papel, t) in enumerate(falas[:5]):
            print(f"   ROLE[{idx}] => {papel}: {t[:120]}")

        if not falas_vendedor:
            print("⚠️ Nenhuma fala de vendedor detectada. Pulando.")
            continue

        # flags de presença por fase e trechos
        spin_final = {fase: 0 for fase in labels}
        textos_por_fase = {fase: [] for fase in labels}

        for i, fala in enumerate(falas_vendedor):
            fala = (fala or "").strip()
            if not fala:
                continue

            try:
                fase = classificar_spin_fase(fala)
                if i < 2:
                    print(f"   SPIN => fase='{fase}' | fala='{fala[:80]}'")
            except Exception as e:
                if i < 2:
                    print(f"   SPIN => ERRO Ollama: {e}")
                # fallback seguro em erro
                fase = spin_fallback_single(fala)

            if fase not in labels:
                fase = "situation"

            # ✅ 1 fala -> 1 fase (SEM mistura)
            spin_final[fase] = 1
            textos_por_fase[fase].append(fala)

        linha = {
            "arquivo": arquivo,
            "processado_em": datetime.now().isoformat(timespec="seconds"),
            "modelo": OLLAMA_MODEL,
        }
        for fase in labels:
            linha[fase] = spin_final[fase]
            linha[f"{fase}_texto"] = " | ".join(textos_por_fase[fase])

        resultados_finais.append(linha)

    df_final = pd.DataFrame(resultados_finais)
    df_final.to_excel(EXCEL_PATH, index=False)

    print("\n✅ ZEROSHOT FINALIZADO (MAIS PRECISO, SEM MISTURAR FASES)")
    print(f"📊 Linhas geradas: {len(df_final)}")
    print(f"📁 Excel salvo em: {EXCEL_PATH}")

if __name__ == "__main__":
    main()
