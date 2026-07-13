"""
Carga masiva de empleados desde CSV (nadie registra 50 empleados a mano).

Formato: nombre;cedula;salario;fecha_ingreso  — con encabezado.
La fecha admite AAAA-MM-DD o DD/MM/AAAA; el salario, formato colombiano.
Reentrante: una cédula ya registrada se actualiza, no se duplica.
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

ENCABEZADO = ["nombre", "cedula", "salario", "fecha_ingreso"]


class ImportacionInvalida(Exception):
    """El archivo no se pudo leer. Mensaje apto para el usuario."""


def _fecha(texto):
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            continue
    raise ValueError(f"fecha inválida «{texto}» (usa AAAA-MM-DD o DD/MM/AAAA)")


def _salario(texto):
    limpio = texto.strip().replace("$", "").replace(" ", "")
    limpio = limpio.replace(".", "").replace(",", ".")  # formato colombiano
    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        raise ValueError(f"salario inválido «{texto}»")
    if valor <= 0:
        raise ValueError("el salario debe ser mayor que cero")
    return valor


def leer_empleados(contenido):
    """Bytes del CSV → (lista de dicts válidos, lista de errores por fila)."""
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportacionInvalida("el archivo no es texto UTF-8 (¿es un CSV?).")

    filas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    filas = [f for f in filas if any(c.strip() for c in f)]
    if not filas:
        raise ImportacionInvalida("el archivo está vacío.")
    encabezado = [c.strip().lower() for c in filas[0]]
    if encabezado[:4] != ENCABEZADO:
        raise ImportacionInvalida(
            "el CSV debe empezar con el encabezado "
            "«nombre;cedula;salario;fecha_ingreso».")

    validos, errores = [], []
    for n, fila in enumerate(filas[1:], start=2):
        if len(fila) < 4:
            errores.append(f"Fila {n}: faltan columnas.")
            continue
        nombre, cedula = fila[0].strip(), fila[1].strip()
        try:
            if not nombre:
                raise ValueError("nombre vacío")
            if not cedula.isdigit():
                raise ValueError(f"cédula inválida «{cedula}» (solo dígitos)")
            validos.append({
                "nombre": nombre,
                "cedula": cedula,
                "salario": _salario(fila[2]),
                "fecha_ingreso": _fecha(fila[3]),
            })
        except ValueError as e:
            errores.append(f"Fila {n} ({nombre or cedula}): {e}.")
    return validos, errores
