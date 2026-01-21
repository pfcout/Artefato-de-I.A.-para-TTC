# ============================================================
# BASE — Funções centrais do Zero-Shot Engine
# ============================================================

import json
import re
import hashlib
from typing import Dict, Any

from zeroshot_engine.functions.ollama_runner import run_ollama_inference


# ============================================================
# 🔹 Inicialização do modelo
# ============================================================
def initialize_model(model_name: str) -> str:
    """
    Inicializa o modelo.
    Mantido simples pois Ollama carrega sob demanda.
    """
    return model_name


# ============================================================
# 🔹 Geração de prompt (CONTRATO DO MOTOR)
# ============================================================
def generate_prompt(
    texto: str,
    fase: str,
    descricao_fase: str
) -> str:
    """
    Gera o prompt zero-shot para uma fase específica.
    """

    return f"""
Você é um classificador especializado em análise de conversas.

TEXTO:
\"\"\"{texto}\"\"\" 

TAREFA:
Verifique se o texto contém a fase "{fase}".

DESCRIÇÃO DA FASE:
{descricao_fase}

INSTRUÇÕES:
- Responda APENAS em JSON
- Use exatamente este formato:

{{"{fase}": 1}}  -> se a fase estiver presente
{{"{fase}": 0}}  -> se a fase NÃO estiver presente
"""


# ============================================================
# 🔹 Identificador estável de prompt (CONTRATO INTERNO)
# ============================================================
def get_prompt_id(prompt_text: str) -> str:
    """
    Gera um ID estável para um prompt.
    Usado para rastreabilidade, métricas e avaliação.
    """
    if not isinstance(prompt_text, str):
        raise ValueError("prompt_text must be a string")

    return hashlib.md5(prompt_text.encode("utf-8")).hexdigest()


# ============================================================
# 🔹 Garantia de saída numérica (0 ou 1)
# ============================================================
def ensure_numeric(value: Any) -> int:
    """
    Normaliza qualquer saída para 0 ou 1.
    """

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return 1 if value == 1 else 0

    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in ["1", "true", "yes", "sim"]:
            return 1
        if cleaned in ["0", "false", "no", "não"]:
            return 0

    return 0


# ============================================================
# 🔹 Envio ao modelo + parse robusto
# ============================================================
def request_to_model(model: str, prompt: str) -> Dict[str, Any]:
    """
    Send the prompt to Ollama, capture output, and parse structured JSON-like responses.
    """

    response = run_ollama_inference(model, prompt)

    try:
        # Remove markdown fences
        response = re.sub(r"```(?:json)?", "", response)
        response = response.replace("```", "").strip()

        # Tenta localizar JSON
        match = re.search(r"\{.*?\}", response, re.DOTALL)
        if match:
            json_str = match.group(0).strip()

            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1]

            json_str = json_str.replace('\\"', '"').replace("'", '"').strip()

            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return parsed

        return {"raw_response": response}

    except Exception:
        return {"raw_response": response}


# ============================================================
# 🔹 Passo único de classificação (COLA DO MOTOR)
# ============================================================
def classification_step(
    model: str,
    texto: str,
    fase: str,
    descricao_fase: str
) -> Dict[str, int]:
    """
    Executa um passo completo de classificação zero-shot:
    - gera prompt
    - envia ao modelo
    - normaliza resposta
    """

    prompt = generate_prompt(
        texto=texto,
        fase=fase,
        descricao_fase=descricao_fase
    )

    response = request_to_model(model, prompt)

    # Caso ideal: {"fase": 1}
    if isinstance(response, dict) and fase in response:
        value = response.get(fase)
        return {fase: ensure_numeric(value)}

    # Caso fallback: modelo respondeu algo estranho
    if isinstance(response, dict):
        for v in response.values():
            return {fase: ensure_numeric(v)}

    return {fase: 0}
