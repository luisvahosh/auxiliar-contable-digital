"""
Exportes de nómina para ENTREGAR al operador (guía P8.9): borrador de pre-PILA
y resumen de nómina electrónica.

Principio (CLAUDE.md): la app es APOYO del auxiliar y causación contable, NO un
software de nómina. Estos exportes NO se presentan ante la PILA ni la DIAN —
son borradores para que el operador de PILA y el proveedor de nómina
electrónica los carguen y verifiquen. El humano presenta.
"""
from decimal import Decimal

from . import parametros as p


def _d(detalle, campo, default="0"):
    return Decimal(str(detalle.get(campo, default) or default))


def _ibc(detalle):
    """IBC (base de cotización). Detalles previos a P8.9 no lo guardan: se
    deriva del aporte de salud del empleado (salud = 4% del IBC)."""
    if detalle.get("ibc"):
        return _d(detalle, "ibc")
    salud = _d(detalle, "salud_empleado")
    return (salud / p.SALUD_EMPLEADO).quantize(Decimal("1")) if salud else Decimal("0")


def _aportes(detalle):
    """Desglose de aportes patronales; {} si el detalle es anterior a P8.9."""
    return {k: Decimal(str(v)) for k, v in (detalle.get("aportes") or {}).items()}


ENCABEZADOS_PRE_PILA = [
    "Cédula", "Nombre", "IBC",
    "Salud empleado", "Salud empleador",
    "Pensión empleado", "Pensión empleador",
    "ARL", "Caja de compensación", "SENA", "ICBF",
    "Total a pagar en la planilla",
]


def filas_pre_pila(liquidacion):
    """Una fila por empleado con el IBC y los aportes (empleado + empleador)."""
    filas = []
    for e in liquidacion.detalle:
        ap = _aportes(e)
        salud_emp = _d(e, "salud_empleado")
        pension_emp = _d(e, "pension_empleado")
        salud_pat = ap.get("salud", Decimal("0"))
        pension_pat = ap.get("pension", Decimal("0"))
        arl = ap.get("arl", Decimal("0"))
        caja = ap.get("caja", Decimal("0"))
        sena = ap.get("sena", Decimal("0"))
        icbf = ap.get("icbf", Decimal("0"))
        total = (salud_emp + salud_pat + pension_emp + pension_pat
                 + arl + caja + sena + icbf)
        filas.append([str(x) for x in [
            e.get("cedula", ""), e.get("empleado", ""), _ibc(e),
            salud_emp, salud_pat, pension_emp, pension_pat,
            arl, caja, sena, icbf, total,
        ]])
    return filas


ENCABEZADOS_NOMINA_ELECTRONICA = [
    "Cédula", "Nombre", "Salario", "Auxilio de transporte", "Otros devengados",
    "Total devengado", "Salud empleado", "Pensión empleado", "Otras deducciones",
    "Total deducciones", "Neto pagado",
]


def filas_nomina_electronica(liquidacion):
    """Devengados y deducciones por empleado, insumo del proveedor de NE."""
    filas = []
    for e in liquidacion.detalle:
        salud = _d(e, "salud_empleado")
        pension = _d(e, "pension_empleado")
        otros = _d(e, "otros_descuentos")
        filas.append([str(x) for x in [
            e.get("cedula", ""), e.get("empleado", ""),
            _d(e, "salario"), _d(e, "auxilio"), _d(e, "novedades_devengo"),
            _d(e, "devengado"), salud, pension, otros,
            salud + pension + otros, _d(e, "neto"),
        ]])
    return filas
