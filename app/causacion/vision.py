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
import io
import json
import os
import re
from decimal import Decimal, InvalidOperation

import requests

TIEMPO_MAXIMO = 60   # los modelos de visión tardan más que los de texto
LADO_MAXIMO = 1600   # px: suficiente para leer una factura, liviano para la API


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
    # Predeterminado elegido por torneo (jul 2026) sobre factura formal,
    # tirilla POS y foto torcida: nemotron-nano-12b-v2-vl 17/18 campos vs
    # llama-3.2-90b 7/18 — además más pequeño y rápido.
    modelo = os.environ.get("IA_VISION_MODELO", "nvidia/nemotron-nano-12b-v2-vl")
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
    "con estas claves exactas: nit_emisor, nombre_emisor, numero, fecha, "
    "subtotal, iva, total, concepto, confianza.\n"
    "Reglas para no equivocarte:\n"
    "- nit_emisor y nombre_emisor son del VENDEDOR que emite la factura (el "
    "negocio del encabezado/logo), NUNCA los del cliente o adquiriente. Solo "
    "dígitos en el NIT, sin puntos ni dígito de verificación (lo que va tras "
    "el guion).\n"
    "- numero es el consecutivo de la factura (suele llevar prefijo de letras, "
    "p. ej. FBS-2041); no es el NIT ni la resolución DIAN.\n"
    "- fecha es la de EMISIÓN/expedición en formato AAAA-MM-DD; si aparece "
    "también fecha de vencimiento, ignórala. Si el día es ambiguo, en Colombia "
    "el formato impreso es día/mes/año.\n"
    "- total es el TOTAL A PAGAR final (después de IVA, propinas y descuentos); "
    "subtotal es la base antes de IVA; debe cumplirse subtotal + iva = total. "
    "Si la factura solo muestra un valor, ese es subtotal y total con iva 0. "
    "Números sin puntos de miles ni signo $.\n"
    "- concepto: qué se compró, en pocas palabras.\n"
    "- confianza: 0 a 100, tu certeza global; si la imagen es borrosa o dudas "
    "de algún campo, baja el número.\n"
    "Si un campo no se lee, usa null — no lo inventes."
)

CAMPOS_ESPERADOS = ("nit_emisor", "nombre_emisor", "numero", "fecha",
                    "subtotal", "iva", "total", "concepto", "confianza")


def preparar_imagen(imagen_bytes, tipo_mime):
    """Acondiciona la foto del celular antes de enviarla al modelo:

    - Aplica la rotación EXIF (los celulares guardan la foto acostada y la
      marcan girada en metadatos — muchos modelos leen fatal así).
    - Reduce el lado mayor a LADO_MAXIMO px y recomprime a JPEG: más rápido
      y lejos de los límites de tamaño de la API, sin perder legibilidad.
    Si algo falla, se envía la imagen original tal cual.
    """
    try:
        from PIL import Image, ImageOps
        imagen = Image.open(io.BytesIO(imagen_bytes))
        imagen = ImageOps.exif_transpose(imagen)
        if max(imagen.size) > LADO_MAXIMO:
            imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
        if imagen.mode != "RGB":
            imagen = imagen.convert("RGB")
        salida = io.BytesIO()
        imagen.save(salida, format="JPEG", quality=88)
        return salida.getvalue(), "image/jpeg"
    except Exception:
        return imagen_bytes, tipo_mime


def _totales_cuadran(campos):
    """True si subtotal + iva == total (o si faltan datos para juzgar)."""
    try:
        subtotal = Decimal(str(campos["subtotal"]))
        iva = Decimal(str(campos["iva"]))
        total = Decimal(str(campos["total"]))
    except (KeyError, TypeError, InvalidOperation):
        return True
    return subtotal + iva == total


def extraer_campos(imagen_bytes, tipo_mime):
    """Imagen → dict con los campos de la factura (o levanta ErrorVision).

    La imagen se acondiciona (rotación EXIF, tamaño) y, si el modelo devuelve
    totales que no cuadran, se reintenta UNA vez diciéndole en qué se equivocó.
    """
    imagen_bytes, tipo_mime = preparar_imagen(imagen_bytes, tipo_mime)
    campos = _extraer(imagen_bytes, tipo_mime, INSTRUCCION)
    if not _totales_cuadran(campos):
        correccion = (
            f"{INSTRUCCION}\n\nOJO: en un intento anterior respondiste "
            f"subtotal={campos.get('subtotal')}, iva={campos.get('iva')}, "
            f"total={campos.get('total')}, y NO cumplen subtotal + iva = total. "
            "Vuelve a leer los tres valores de la imagen con máximo cuidado."
        )
        segundo = _extraer(imagen_bytes, tipo_mime, correccion)
        if _totales_cuadran(segundo):
            return segundo
        # Ninguno cuadró: se entrega el primero con confianza degradada;
        # el usuario corrige en la pantalla de confirmación.
        try:
            campos["confianza"] = min(int(campos.get("confianza") or 50), 40)
        except (TypeError, ValueError):
            campos["confianza"] = 40
    return campos


def _extraer(imagen_bytes, tipo_mime, instruccion):
    url, modelo, key = _configuracion()
    imagen_b64 = base64.b64encode(imagen_bytes).decode()
    cuerpo = {
        "model": modelo,
        "temperature": 0,
        "max_tokens": 512,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": instruccion},
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

    # El modelo a veces envuelve el JSON en prosa o en ```; tomar el primer {...}
    encontrado = re.search(r"\{.*\}", texto, re.DOTALL)
    if not encontrado:
        raise ErrorVision(
            "la IA no pudo leer una factura en esa imagen; intenta con una foto "
            "más nítida y completa (o digita los campos manualmente)."
        )
    try:
        campos = json.loads(encontrado.group(0))
    except ValueError:
        raise ErrorVision("la IA no devolvió datos legibles; intenta con una foto más nítida.")
    if not isinstance(campos, dict):
        raise ErrorVision("la IA no devolvió datos legibles; intenta con una foto más nítida.")
    return {clave: campos.get(clave) for clave in CAMPOS_ESPERADOS}
