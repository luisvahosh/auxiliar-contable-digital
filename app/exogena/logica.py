"""
Pre-armado de información exógena (guía P12): formatos 1001 y 1007.

Agrega por tercero desde los documentos ya causados del año — cero digitación.
Es apoyo del auxiliar: arma el borrador; el humano lo revisa y lo presenta en
el prevalidador de la DIAN. Los conceptos DIAN aquí son los más comunes; se
confirman contra la resolución del año (que cambia códigos y cuantías).
"""
from decimal import Decimal

from causacion.models import FacturaCompra, FacturaVenta

# Concepto de retención (interno) → concepto DIAN del formato 1001.
# Confirmar contra la resolución de exógena del año (los códigos varían).
CONCEPTO_DIAN_1001 = {
    "honorarios": ("5001", "Honorarios"),
    "servicios": ("5004", "Servicios"),
    "compras": ("5007", "Compras"),
    "arrendamiento_inmueble": ("5010", "Arrendamientos"),
    "": ("5016", "Otros costos y deducciones"),
}
CONCEPTO_DIAN_1007 = ("4001", "Ingresos brutos de actividades ordinarias")


def _tipo_documento(nit):
    # 31 = NIT (persona jurídica), 13 = cédula (persona natural)
    return "31" if len(nit.strip()) >= 9 else "13"


def formato_1001(empresa, anio):
    """Pagos o abonos en cuenta y retenciones practicadas, por tercero.
    Descuenta las notas crédito de proveedor (neto). → dict con filas y total."""
    compras = FacturaCompra.objects.de_empresa(empresa).filter(
        tipo="compra", estado="aprobada", fecha_emision__year=anio)

    # (nit, nombre, concepto) -> {base, retencion}
    grupos = {}
    for f in compras:
        clave = (f.nit_emisor, f.nombre_emisor, f.concepto_retencion or "")
        g = grupos.setdefault(clave, {"base": Decimal("0"), "retencion": Decimal("0")})
        g["base"] += f.subtotal
        g["retencion"] += f.retencion

    # P12.6: las notas crédito de proveedor descuentan la base
    notas = (FacturaCompra.objects.de_empresa(empresa)
             .filter(tipo="nota_credito", estado="aprobada",
                     fecha_emision__year=anio, factura_original__isnull=False)
             .select_related("factura_original"))
    for nc in notas:
        orig = nc.factura_original
        clave = (orig.nit_emisor, orig.nombre_emisor, orig.concepto_retencion or "")
        if clave in grupos:
            grupos[clave]["base"] -= nc.subtotal

    filas, total_base, total_ret = [], Decimal("0"), Decimal("0")
    for (nit, nombre, concepto), v in sorted(grupos.items(), key=lambda x: x[0][1]):
        cod, nom = CONCEPTO_DIAN_1001.get(concepto, CONCEPTO_DIAN_1001[""])
        filas.append({
            "tipo_doc": _tipo_documento(nit), "nit": nit, "nombre": nombre,
            "concepto": cod, "concepto_nombre": nom,
            "base": v["base"], "retencion": v["retencion"],
        })
        total_base += v["base"]
        total_ret += v["retencion"]
    return {"filas": filas, "total_base": total_base, "total_retencion": total_ret}


def formato_1007(empresa, anio):
    """Ingresos recibidos por tercero (cliente). Descuenta notas crédito de
    venta (neto). → dict con filas y total."""
    ventas = FacturaVenta.objects.de_empresa(empresa).filter(
        tipo="venta", estado="aprobada", fecha_emision__year=anio)

    grupos = {}  # (nit, nombre) -> ingreso
    for v in ventas:
        clave = (v.nit_cliente, v.nombre_cliente)
        grupos[clave] = grupos.get(clave, Decimal("0")) + v.subtotal

    notas = (FacturaVenta.objects.de_empresa(empresa)
             .filter(tipo="nota_credito", estado="aprobada",
                     fecha_emision__year=anio, factura_original__isnull=False))
    for nc in notas:
        clave = (nc.nit_cliente, nc.nombre_cliente)
        if clave in grupos:
            grupos[clave] -= nc.subtotal

    cod, nom = CONCEPTO_DIAN_1007
    filas, total = [], Decimal("0")
    for (nit, nombre), ingreso in sorted(grupos.items(), key=lambda x: x[0][1]):
        filas.append({
            "tipo_doc": _tipo_documento(nit), "nit": nit, "nombre": nombre,
            "concepto": cod, "concepto_nombre": nom, "ingreso": ingreso,
        })
        total += ingreso
    return {"filas": filas, "total": total}
