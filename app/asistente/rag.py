"""
RAG del asistente normativo: recupera las fichas relevantes del corpus y
responde SOLO con ellas, citando la fuente. Nunca responde de memoria del
modelo — así no inventa normatividad.

Búsqueda semántica (embeddings + coseno en Python; el corpus es acotado, no
necesita pgvector) con respaldo por coincidencia de términos si no hay
embeddings. La respuesta la redacta un LLM con el contexto recuperado; si el
LLM no está disponible, se devuelven las fichas tal cual.
"""
import math
import os
import re
import unicodedata

import requests

from .embeddings import embed
from .models import ArticuloNormativo

TIEMPO_MAXIMO = 60
TOP_K = 3
DIAS_CACHE = 30

DISCLAIMER = ("Esta es una orientación general de apoyo, no asesoría oficial. "
              "Valídala con tu contador y contra el texto vigente de la norma.")


def _coseno(a, b):
    if not a or not b or len(a) != len(b):
        return -1.0
    punto = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return punto / (na * nb) if na and nb else -1.0


def _normalizar(texto):
    """Minúsculas sin acentos, para que «retencion» matchee «retención»."""
    sin = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def _terminos(texto):
    return {t for t in re.findall(r"[a-zñ]{4,}", _normalizar(texto))}


def recuperar(pregunta, k=TOP_K):
    """Las k fichas más relevantes para la pregunta."""
    corpus = list(ArticuloNormativo.objects.all())
    if not corpus:
        return []

    vector = embed(pregunta, tipo="query")
    indexado = [a for a in corpus if a.embedding]
    if vector and indexado:
        rankeado = sorted(indexado, key=lambda a: _coseno(vector, a.embedding),
                          reverse=True)
        return rankeado[:k]

    # Respaldo: coincidencia de términos (funciona sin API). El título pesa
    # más que el cuerpo, y cuenta la frecuencia para desempatar.
    terminos = _terminos(pregunta)
    with_score = []
    for a in corpus:
        campo = _normalizar((a.titulo + " ") * 3 + a.referencia + " " + a.texto)
        palabras = re.findall(r"[a-zñ]{4,}", campo)
        score = sum(palabras.count(t) for t in terminos)
        if score:
            with_score.append((score, a))
    with_score.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in with_score[:k]]


def _responder_con_llm(pregunta, fichas):
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not key:
        return None
    url = os.environ.get("IA_ASISTENTE_URL",
                         "https://integrate.api.nvidia.com/v1").rstrip("/")
    # 8b elegido por benchmark (jul 2026): ~1.4s vs el 70b que no respondía a
    # tiempo; misma calidad para respuestas cortas sobre contexto acotado.
    modelo = os.environ.get("IA_ASISTENTE_MODELO",
                            "meta/llama-3.1-8b-instruct")
    contexto = "\n\n".join(
        f"[{a.referencia}] {a.titulo}\n{a.texto}" for a in fichas)
    instruccion = (
        "Eres un asistente para un auxiliar contable colombiano. Responde la "
        "pregunta USANDO ÚNICAMENTE el contexto normativo dado; si el contexto "
        "no alcanza, dilo y sugiere validar con el contador. Responde en "
        "español, claro y breve, citando la referencia (art. …) de donde sacas "
        "cada afirmación. No inventes cifras ni artículos.\n\n"
        f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}")
    try:
        respuesta = requests.post(
            f"{url}/chat/completions",
            json={"model": modelo, "temperature": 0.1, "max_tokens": 450,
                  "messages": [{"role": "user", "content": instruccion}]},
            headers={"Authorization": f"Bearer {key}"}, timeout=TIEMPO_MAXIMO)
        if not respuesta.ok:
            return None
        return respuesta.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


def _clave_cache(pregunta):
    # Sin acentos, sin puntuación, espacios colapsados: «¿Retención?» = «retencion»
    limpio = re.sub(r"[^a-z0-9ñ ]", " ", _normalizar(pregunta))
    return re.sub(r"\s+", " ", limpio).strip()[:500]


def consultar(pregunta):
    """→ dict con respuesta, fichas fuente y disclaimer.
    Cachea la respuesta por pregunta normalizada: una repetida no llama a la IA."""
    from datetime import timedelta

    from django.utils import timezone

    from .models import ConsultaCache

    clave = _clave_cache(pregunta)
    reciente = ConsultaCache.objects.filter(
        pregunta=clave, creada__gte=timezone.now() - timedelta(days=DIAS_CACHE)
    ).first()
    if reciente:
        fichas = list(ArticuloNormativo.objects.filter(tema__in=reciente.fuentes))
        return {"respuesta": reciente.respuesta, "fuentes": fichas,
                "disclaimer": DISCLAIMER, "cacheada": True}

    fichas = recuperar(pregunta)
    if not fichas:
        return {
            "respuesta": "No encontré nada en el corpus normativo sobre eso. "
                         "Reformula la pregunta o pide al administrador que "
                         "cargue el tema. " + DISCLAIMER,
            "fuentes": [], "disclaimer": DISCLAIMER,
        }
    respuesta = _responder_con_llm(pregunta, fichas)
    if respuesta is None:
        # Sin LLM: se entregan las fichas recuperadas como respuesta
        respuesta = ("El asistente de redacción no está disponible; estas son "
                     "las fichas más relacionadas con tu pregunta:\n\n" +
                     "\n\n".join(f"• {a.titulo} ({a.referencia}): {a.texto}"
                                 for a in fichas))
        return {"respuesta": respuesta, "fuentes": fichas, "disclaimer": DISCLAIMER}

    # Solo se cachean respuestas del LLM (las de respaldo no)
    ConsultaCache.objects.update_or_create(
        pregunta=clave,
        defaults={"respuesta": respuesta, "fuentes": [a.tema for a in fichas]})
    return {"respuesta": respuesta, "fuentes": fichas, "disclaimer": DISCLAIMER,
            "cacheada": False}
