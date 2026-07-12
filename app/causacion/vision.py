"""
Extracción de campos de una factura física fotografiada (caso P1.10).

Proveedor: endpoint de visión OpenAI-compatible del catálogo NVIDIA NIM
(PLAN.md §4). Configuración por .env: NVIDIA_API_KEY obligatoria;
IA_VISION_URL e IA_VISION_MODELO opcionales para cambiar de proveedor/modelo
sin tocar código.

Reglas P1.10:
- Lo extraído entra SIEMPRE como propuesta "sugerida": el OCR se equivoca y
  el usuario confirma campo por campo antes de causar.
- Minimización de datos (Ley 1581): solo viaja la imagen y la instrucción de
  extracción; nada del tenant. No se loguea el contenido.
"""
import base64
import json
import os

import requests

TIEMPO_MAXIMO = 60  # los modelos de visión tardan más que los de texto


class VisionNoConfigurada(Exception):
    """Falta NVIDIA_API_KEY en .env."""


class ErrorVision(Exception):
    """El servicio de visión falló. Mensaje apto para el usuario."""


def _configuracion():
    key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not key:
        raise VisionNoConfigurada(
            "La IA de visión no está configurada: define NVIDIA_API_KEY en el .env "
            "(key gratuita en build.nvidia.com)."
        )
    url = os.environ.get("IA_VISION_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    modelo = os.environ.get("IA_VISION_MODELO", "meta/llama-3.2-90b-vision-instruct")
    return url, modelo, key


def esta_configurada():
    try:
        _configuracion()
        return True
    except VisionNoConfigurada:
        return False


INSTRUCCION = (
    "Eres un auxiliar contable colombiano. Extrae de la imagen de esta factura "
    "los campos y responde SOLO un objeto JSON válido, sin markdown ni comentarios, "
    "con estas claves exactas: nit_emisor (solo dígitos, sin dígito de verificación), "
    "nombre_emisor, numero (número de la factura), fecha (AAAA-MM-DD), "
    "subtotal (número, sin puntos de miles), iva (número), total (número), "
    "concepto (qué se facturó, breve), confianza (0 a 100, tu certeza global). "
    "Si un campo no se lee, usa null."
)

CAMPOS_ESPERADOS = ("nit_emisor", "nombre_emisor", "numero", "fecha",
                    "subtotal", "iva", "total", "concepto", "confianza")


def extraer_campos(imagen_bytes, tipo_mime):
    """Imagen → dict con los campos de la factura (o levanta ErrorVision)."""
    url, modelo, key = _configuracion()
    imagen_b64 = base64.b64encode(imagen_bytes).decode()
    cuerpo = {
        "model": modelo,
        "temperature": 0,
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": INSTRUCCION},
                {"type": "image_url",
                 "image_url": {"url": f"data:{tipo_mime};base64,{imagen_b64}"}},
            ],
        }],
    }
    try:
        respuesta = requests.post(f"{url}/chat/completions", json=cuerpo,
                                  headers={"Authorization": f"Bearer {key}"},
                                  timeout=TIEMPO_MAXIMO)
    except requests.RequestException:
        raise ErrorVision("no se pudo conectar con el servicio de visión; intenta de nuevo.")

    if respuesta.status_code == 401:
        raise ErrorVision("el servicio rechazó la NVIDIA_API_KEY; revísala en el .env.")
    if not respuesta.ok:
        raise ErrorVision(f"el servicio de visión respondió con error {respuesta.status_code}.")

    try:
        texto = respuesta.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError):
        raise ErrorVision("respuesta inesperada del servicio de visión.")

    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`").removeprefix("json").strip()
    try:
        campos = json.loads(texto)
    except ValueError:
        raise ErrorVision("la IA no devolvió datos legibles; intenta con una foto más nítida.")
    if not isinstance(campos, dict):
        raise ErrorVision("la IA no devolvió datos legibles; intenta con una foto más nítida.")
    return {clave: campos.get(clave) for clave in CAMPOS_ESPERADOS}
