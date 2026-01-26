import os
import requests

def transcribe_via_vps(uploaded_file) -> dict:
    """
    Envia WAV para o VPS e retorna o JSON completo:
    { text_raw, lines_raw, lines_labeled, text_labeled, duration, language }
    """
    url = os.getenv("TRANSCRIBE_API_URL", "").strip()
    if not url:
        raise RuntimeError("TRANSCRIBE_API_URL não definido.")

    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    r = requests.post(url, files=files, timeout=600)
    r.raise_for_status()
    return r.json()


def transcribe_audio(uploaded_file) -> dict:
    """
    Modo padrão (recomendado): VPS
    Você pode alternar por variável de ambiente TRANSCRIBE_MODE.
    """
    mode = os.getenv("TRANSCRIBE_MODE", "VPS").upper().strip()

    if mode == "VPS":
        return transcribe_via_vps(uploaded_file)

    # Se você quiser, depois plugamos o 01 local aqui.
    # Por enquanto, mantenha VPS no deploy e no local se quiser.
    raise RuntimeError("TRANSCRIBE_MODE=LOCAL ainda não implementado neste gateway.")
