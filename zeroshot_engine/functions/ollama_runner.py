# ============================================================
# OLLAMA RUNNER — CPU / GPU AGNÓSTICO
# ============================================================

import subprocess


def run_ollama_inference(model: str, prompt: str) -> str:
    """
    Executa inferência no Ollama.
    Usa GPU automaticamente se disponível (Ollama decide).
    """

    try:
        process = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            text=True,
            capture_output=True,
            encoding="utf-8"
        )

        if process.returncode != 0:
            raise RuntimeError(process.stderr)

        return process.stdout.strip()

    except FileNotFoundError:
        raise RuntimeError(
            "❌ Ollama CLI não encontrado. Verifique instalação e PATH."
        )

    except Exception as e:
        raise RuntimeError(f"❌ Erro na inferência Ollama: {e}")
