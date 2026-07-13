"""
Certificados de retención en la fuente por tercero (guía P9).

Agrega desde las facturas de compra aprobadas del año — cero digitación:
por cada proveedor al que se le retuvo, suma bases y retenciones por concepto.
La retención total del certificado es la efectivamente practicada (créditos a
2365) y por eso cuadra con lo que la empresa declara como agente retenedor
(P9.4). Las notas crédito de proveedor descuentan la base (P9.3); la retención
practicada no se ajusta salvo nota de ajuste (queda advertido).
"""
from decimal import Decimal

from .clasificacion import CONCEPTOS_RETENCION
from .models import FacturaCompra


def _nombre_concepto(concepto):
    datos = CONCEPTOS_RETENCION.get(concepto)
    return datos["nombre"] if datos else (concepto or "Sin concepto")


def certificados_del_anio(empresa, anio):
    """Estructura con un certificado por tercero + el cuadre contra 2365."""
    compras = FacturaCompra.objects.de_empresa(empresa).filter(
        tipo="compra", estado="aprobada", fecha_emision__year=anio,
        retencion__gt=0)

    # (nit, nombre) -> concepto -> {base, retencion}
    terceros = {}
    for factura in compras:
        clave = (factura.nit_emisor, factura.nombre_emisor)
        conceptos = terceros.setdefault(clave, {})
        rubro = conceptos.setdefault(
            factura.concepto_retencion, {"base": Decimal("0"), "retencion": Decimal("0")})
        rubro["base"] += factura.subtotal
        rubro["retencion"] += factura.retencion

    # P9.3: las notas crédito de proveedor aprobadas del año descuentan la base
    notas = (FacturaCompra.objects.de_empresa(empresa)
             .filter(tipo="nota_credito", estado="aprobada",
                     fecha_emision__year=anio, factura_original__isnull=False)
             .select_related("factura_original"))
    for nota in notas:
        original = nota.factura_original
        if original.retencion <= 0:
            continue
        conceptos = terceros.get((original.nit_emisor, original.nombre_emisor))
        if conceptos and original.concepto_retencion in conceptos:
            conceptos[original.concepto_retencion]["base"] -= nota.subtotal

    lista = []
    total_retencion = Decimal("0")
    for (nit, nombre), conceptos in sorted(terceros.items(), key=lambda x: x[0][1]):
        filas = []
        base_t = retencion_t = Decimal("0")
        for concepto, rubro in sorted(conceptos.items()):
            filas.append({
                "concepto": concepto,
                "nombre_concepto": _nombre_concepto(concepto),
                "base": rubro["base"],
                "retencion": rubro["retencion"],
            })
            base_t += rubro["base"]
            retencion_t += rubro["retencion"]
        total_retencion += retencion_t
        lista.append({
            "nit": nit, "nombre": nombre, "conceptos": filas,
            "total_base": base_t, "total_retencion": retencion_t,
        })

    retencion_en_asientos = _retencion_en_asientos(compras)
    return {
        "anio": anio,
        "terceros": lista,
        "total_retencion": total_retencion,
        "retencion_en_asientos": retencion_en_asientos,
        # P9.4: la retención practicada del año = créditos a 2365 de los asientos
        "cuadra": total_retencion == retencion_en_asientos,
    }


def _retencion_en_asientos(compras):
    total = Decimal("0")
    for factura in compras:
        for renglon in factura.asiento:
            if renglon["cuenta"].startswith("2365"):
                total += Decimal(renglon["credito"])
    return total


def certificado_de(empresa, anio, nit):
    """Detalle imprimible del certificado de un proveedor: conceptos + las
    facturas que lo respaldan."""
    datos = certificados_del_anio(empresa, anio)
    tercero = next((t for t in datos["terceros"] if t["nit"] == nit), None)
    if tercero is None:
        return None
    facturas = FacturaCompra.objects.de_empresa(empresa).filter(
        tipo="compra", estado="aprobada", fecha_emision__year=anio,
        retencion__gt=0, nit_emisor=nit).order_by("fecha_emision")
    return {"anio": anio, "empresa": empresa, "tercero": tercero, "facturas": facturas}
