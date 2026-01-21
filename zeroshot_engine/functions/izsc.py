# ============================================================
# IZSC — Interpretação Zero-Shot por Fase
# Compatível com SPIN / scripts_base / Ollama
# ============================================================

import json
from typing import Dict, Any, List


# ============================================================
# 🔹 Função esperada pelo motor (CONTRATO OFICIAL)
# ============================================================
def set_zeroshot_parameters(
    response: Any = None,
    current_key: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Interface oficial usada pelo motor zeroshot.

    Aceita kwargs extras para compatibilidade
    com versões antigas do motor.
    """
    if current_key is None:
        return {}

    return parse_izsc_response(response, current_key)


# ============================================================
# 🔹 Classificação zero-shot de UMA fase
# (exigida pelo __init__.py)
# ============================================================
def single_iterative_zeroshot_classification(
    response: Any,
    phase_key: str,
    **kwargs
) -> Dict[str, int]:
    """
    Classificação zero-shot para uma única fase.
    """

    parsed = parse_izsc_response(response, phase_key)
    value = parsed.get(phase_key, 0)

    return {phase_key: 1 if value else 0}


# ============================================================
# 🔹 Classificação iterativa (CONTRATO DO SCRIPT 02_zeroshot.py)
# ============================================================
def iterative_zeroshot_classification(
    responses: List[Any] = None,
    phase_keys: List[str] = None,
    **kwargs
) -> Dict[str, int]:
    """
    Executa a classificação zero-shot fase a fase.

    Compatível com chamadas do tipo:
    iterative_zeroshot_classification(
        text=..., model=..., prompts=..., feedback=True
    )
    """

    # 🔹 Compatibilidade com chamadas antigas
    if responses is None:
        responses = kwargs.get("responses", [])

    if phase_keys is None:
        phase_keys = kwargs.get("phase_keys", [])

    results: Dict[str, int] = {}

    for response, key in zip(responses, phase_keys):
        parsed = parse_izsc_response(response, key)
        value = parsed.get(key, 0)
        results[key] = 1 if value else 0

    return results


# ============================================================
# 🔹 Parser robusto (SEU CÓDIGO, PRESERVADO)
# ============================================================
def parse_izsc_response(
    response: Any,
    current_key: str
) -> Dict[str, Any]:
    """
    Parse robusto da resposta do modelo zero-shot.
    """

    try:
        # 🔹 Já estruturado
        if isinstance(response, dict):
            parsed_response = response

        # 🔹 String (Ollama)
        elif isinstance(response, str):
            cleaned = response.strip().lower().strip('"{} ')

            # Nome da fase puro (ex: "abertura")
            if cleaned == current_key.lower():
                parsed_response = {current_key: 1}

            # JSON (normal ou escapado)
            elif "{" in cleaned and "}" in cleaned:
                cleaned_json = response.strip().replace('\\"', '"')

                if cleaned_json.startswith('"') and cleaned_json.endswith('"'):
                    cleaned_json = cleaned_json[1:-1]

                parsed_response = json.loads(cleaned_json)

            # Positivo implícito
            elif "1" in cleaned or "true" in cleaned:
                parsed_response = {current_key: 1}

            # Negativo implícito
            elif "0" in cleaned or "false" in cleaned:
                parsed_response = {current_key: 0}

            else:
                parsed_response = {current_key: 0}

        else:
            raise ValueError("Formato de resposta inesperado.")

        if not isinstance(parsed_response, dict):
            raise ValueError("Resposta não é um dicionário válido.")

        return parsed_response

    except Exception as e:
        print(f"❌ Erro ao processar JSON da fase '{current_key}': {e}")
        return {
            current_key: 0,
            "error": str(e),
            "raw_response": str(response)
        }
