"""
Embeddings del corpus y de las preguntas, vía el endpoint OpenAI-compatible
de NVIDIA (misma NVIDIA_API_KEY de la visión). Si no hay key o el servicio
falla, se devuelve None y el RAG cae a búsqueda por términos.
"""
import os

import requests

TIEMPO_MAXIMO = 30


def _config():
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not key:
        return None
    url = os.environ.get("IA_ASISTENTE_URL",
                         "https://integrate.api.nvidia.com/v1").rstrip("/")
    modelo = os.environ.get("IA_EMBED_MODELO", "nvidia/nv-embedqa-e5-v5")
    return url, modelo, key


def esta_configurado():
    return _config() is not None


def embed(texto, tipo="query"):
    """Vector del texto (lista de floats) o None si no se pudo."""
    config = _config()
    if config is None:
        return None
    url, modelo, key = config
    try:
        respuesta = requests.post(
            f"{url}/embeddings",
            json={"input": [texto], "model": modelo,
                  "input_type": "passage" if tipo == "passage" else "query"},
            headers={"Authorization": f"Bearer {key}"}, timeout=TIEMPO_MAXIMO)
        if not respuesta.ok:
            return None
        return respuesta.json()["data"][0]["embedding"]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None
