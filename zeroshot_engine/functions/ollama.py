import os
import subprocess
import platform
import time


# ==========================================================
# SIMPLE OLLAMA INITIALIZATION (CPU ONLY)
# ==========================================================

def check_ollama_installation():
    """
    Verify if Ollama is installed and accessible in the system PATH.
    """
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Ollama detected: {result.stdout.strip()}")
            return True
        else:
            print("⚠️ Ollama command found but returned an error.")
            return False
    except FileNotFoundError:
        print("❌ Ollama not found in PATH. Please install from https://ollama.com/download")
        return False


def start_ollama_service():
    """
    Ensure the Ollama service is running.
    Tries to start it silently if not already running.
    """
    try:
        system_name = platform.system()

        if system_name == "Windows":
            ollama_path = os.path.expanduser("~\\AppData\\Local\\Programs\\Ollama\\ollama.exe")
            if os.path.exists(ollama_path):
                print("Starting Ollama service (Windows)...")
                subprocess.Popen(
                    [ollama_path],
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                time.sleep(3)
                print("Ollama service started successfully.")
                return True
            else:
                print("⚠️ Ollama executable not found at default path.")
                return False

        else:
            # macOS / Linux
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("Ollama service started successfully (Unix-like).")
            return True

    except Exception as e:
        print(f"⚠️ Error while starting Ollama service: {e}")
        return False


def verify_model_available(model_name: str):
    """
    Check if a given model is available locally in Ollama.
    Downloads it if missing.
    """
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if model_name in result.stdout:
            print(f"✅ Model '{model_name}' is available locally.")
            return True
        else:
            print(f"⬇️ Model '{model_name}' not found. Downloading now...")
            subprocess.run(["ollama", "pull", model_name], check=True)
            print(f"✅ Model '{model_name}' downloaded successfully.")
            return True
    except Exception as e:
        print(f"❌ Error checking/downloading model '{model_name}': {e}")
        return False


def setup_ollama(model_name: str = "gemma2:2b"):
    """
    Perform minimal Ollama setup:
    - Check installation
    - Start service
    - Ensure model exists locally
    """
    if not check_ollama_installation():
        raise RuntimeError("Ollama is not installed or not found in PATH.")

    start_ollama_service()
    verify_model_available(model_name)
    print("✅ Ollama setup completed (CPU only).")

# ==========================================================
# 🔹 Verificação de updates do Ollama (stub seguro)
# ==========================================================
def check_ollama_updates() -> bool:
    """
    Verifica se há updates do Ollama.
    Atualmente é um stub seguro para manter compatibilidade do motor.

    Retorna:
    True -> sistema operacional
    """

    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"ℹ️ Ollama version: {result.stdout.strip()}")
            return True

        print("⚠️ Não foi possível verificar a versão do Ollama.")
        return False

    except Exception as e:
        print(f"⚠️ Falha ao verificar updates do Ollama: {e}")
        return False
