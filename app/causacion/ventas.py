"""
Registro de facturas de venta emitidas por la empresa (guía P2).

El asiento de venta: débito a cartera (1305) por el neto que pagará el
cliente, débito a 135515 por la retefuente que el cliente practica (anticipo
de impuestos a favor), crédito al ingreso (4135) y al IVA generado (240801).
La nota crédito reversa: débito ingreso + IVA, crédito cartera, vinculada a
la factura original. Control P2.3: el consecutivo no puede tener huecos.
"""
import re
from decimal import Decimal

from .parametros import (
    CUENTA_CLIENTES,
    CUENTA_INGRESOS,
    CUENTA_IVA_GENERADO,
    CUENTA_RETEFUENTE_A_FAVOR,
)

_PATRON_CONSECUTIVO = re.compile(r"^(.*?)(\d+)$")


def _renglon(cuenta, nombre, debito=Decimal("0"), credito=Decimal("0")):
    return {"cuenta": cuenta, "nombre": nombre,
            "debito": str(debito), "credito": str(credito)}


def _verificar_balance(renglones):
    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        raise ValueError(f"Asiento desbalanceado: débitos {debitos} ≠ créditos {creditos}.")
    return renglones


def construir_asiento_venta(factura):
    """Renglones del registro de una venta. Devuelve (renglones, explicación)."""
    retenido = factura.retefuente_practicada
    renglones = [
        _renglon(*CUENTA_CLIENTES, debito=factura.total - retenido),
    ]
    partes = [
        f"Venta {factura.numero} a {factura.nombre_adquiriente}: ingreso "
        f"${factura.subtotal:,.0f} (4135) más IVA generado ${factura.iva:,.0f} (240801)."
    ]
    if retenido > 0:
        renglones.append(_renglon(*CUENTA_RETEFUENTE_A_FAVOR, debito=retenido))
        partes.append(
            f"El cliente practica retefuente por ${retenido:,.0f} (viene en el XML): "
            "queda en 135515 como anticipo a favor y la cartera se registra por el neto."
        )
    else:
        partes.append("El cliente no practica retención: cartera por el total.")
    renglones.append(_renglon(*CUENTA_INGRESOS, credito=factura.subtotal))
    if factura.iva > 0:
        renglones.append(_renglon(*CUENTA_IVA_GENERADO, credito=factura.iva))
    return _verificar_balance(renglones), " ".join(partes)


def construir_asiento_nota_credito(nota, original):
    """Reversa (parcial o total) de una venta ya registrada."""
    renglones = [
        _renglon(*CUENTA_INGRESOS, debito=nota.subtotal),
    ]
    if nota.iva > 0:
        renglones.append(_renglon(*CUENTA_IVA_GENERADO, debito=nota.iva))
    renglones.append(_renglon(*CUENTA_CLIENTES, credito=nota.total))
    alcance = "total" if nota.total == original.total else "parcial"
    explicacion = (
        f"Nota crédito {nota.numero}: reversa {alcance} de la venta "
        f"{original.numero} (${nota.total:,.0f} de ${original.total:,.0f}). "
        "Se debita el ingreso y el IVA generado y se descarga la cartera del cliente."
    )
    return _verificar_balance(renglones), explicacion


def separar_consecutivo(numero):
    """'FE-104' → ('FE-', 104). Si el número no termina en dígitos: (numero, None)."""
    coincidencia = _PATRON_CONSECUTIVO.match(numero)
    if not coincidencia:
        return numero, None
    return coincidencia.group(1), int(coincidencia.group(2))


def consecutivos_faltantes(numeros):
    """Control P2.3: huecos en la numeración de facturas emitidas.

    Recibe los números de venta ya registrados (sin notas crédito) y devuelve
    la lista de faltantes, p. ej. ['FE-105'].
    """
    por_prefijo = {}
    for numero in numeros:
        prefijo, consecutivo = separar_consecutivo(numero)
        if consecutivo is not None:
            por_prefijo.setdefault(prefijo, set()).add(consecutivo)
    faltantes = []
    for prefijo, vistos in sorted(por_prefijo.items()):
        for n in range(min(vistos), max(vistos)):
            if n not in vistos:
                faltantes.append(f"{prefijo}{n}")
    return faltantes
