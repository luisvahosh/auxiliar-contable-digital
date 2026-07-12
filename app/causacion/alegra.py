"""
Cliente mínimo de la API de Alegra: crear el asiento contable (journal)
de una factura aprobada.

Configuración por .env (12-factor): ALEGRA_EMAIL + ALEGRA_TOKEN (el token
se genera en Alegra: Configuración → Integraciones → API). Sin credenciales
la app lo dice claro y no intenta nada.

Privacidad (CLAUDE.md §4): a Alegra viaja solo lo indispensable del asiento
(fecha, cuentas, valores, número de factura); nada se escribe en logs.
"""
import os
from decimal import Decimal

import requests

URL_BASE = "https://api.alegra.com/api/v1"
TIEMPO_MAXIMO = 20  # segundos


class AlegraNoConfigurado(Exception):
    """Faltan ALEGRA_EMAIL/ALEGRA_TOKEN en .env."""


class ErrorAlegra(Exception):
    """La API de Alegra rechazó la petición. Mensaje apto para el usuario."""


def _credenciales():
    correo = os.environ.get("ALEGRA_EMAIL", "").strip()
    token = os.environ.get("ALEGRA_TOKEN", "").strip()
    if not correo or not token:
        raise AlegraNoConfigurado(
            "Alegra no está configurado: define ALEGRA_EMAIL y ALEGRA_TOKEN en el .env "
            "(el token se genera en Alegra → Configuración → Integraciones → API)."
        )
    return correo, token


def esta_configurado():
    try:
        _credenciales()
        return True
    except AlegraNoConfigurado:
        return False


def enviar_asiento(factura, mapeo_cuentas):
    """Crea el journal en Alegra y devuelve su id.

    mapeo_cuentas: dict {cuenta PUC local -> id de cuenta contable en Alegra}.
    El plan de cuentas de Alegra tiene ids propios; el mapeo vive por empresa
    en MapeoCuentaAlegra y debe cubrir todas las cuentas del asiento.
    """
    correo, token = _credenciales()

    faltantes = sorted({r["cuenta"] for r in factura.asiento} - set(mapeo_cuentas))
    if faltantes:
        raise ErrorAlegra(
            "Faltan cuentas por mapear a Alegra: " + ", ".join(faltantes) +
            ". Regístralas en el admin (Mapeos de cuenta Alegra)."
        )

    # Formato del endpoint /journals: cada movimiento lleva el id de la cuenta
    # en "id" y SOLO debit o credit (nunca ambos, aunque sea en cero).
    movimientos = []
    for r in factura.asiento:
        movimiento = {
            "id": mapeo_cuentas[r["cuenta"]],
            "description": f"{r['cuenta']} {r['nombre']}"[:255],
        }
        debito = Decimal(r["debito"])
        if debito > 0:
            movimiento["debit"] = float(debito)
        else:
            movimiento["credit"] = float(Decimal(r["credito"]))
        movimientos.append(movimiento)

    cuerpo = {
        "date": factura.fecha_emision.isoformat(),
        "reference": f"Factura {factura.numero}"[:255],
        "observations": (f"Causación factura {factura.numero} — {factura.nombre_tercero} "
                         f"(NIT {factura.nit_tercero}). Generado por Auxiliar Contable Digital.")[:500],
        "entries": movimientos,
    }

    try:
        respuesta = requests.post(f"{URL_BASE}/journals", json=cuerpo,
                                  auth=(correo, token), timeout=TIEMPO_MAXIMO)
    except requests.RequestException:
        raise ErrorAlegra("No se pudo conectar con Alegra (¿hay internet?). Intenta de nuevo.")

    if respuesta.status_code == 401:
        raise ErrorAlegra("Alegra rechazó las credenciales: revisa ALEGRA_EMAIL y ALEGRA_TOKEN.")
    if not respuesta.ok:
        detalle = ""
        try:
            detalle = respuesta.json().get("message", "")
        except ValueError:
            pass
        raise ErrorAlegra(f"Alegra rechazó el asiento ({respuesta.status_code}). {detalle}".strip())

    return str(respuesta.json().get("id", ""))
