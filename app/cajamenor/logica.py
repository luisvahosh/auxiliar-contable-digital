"""
Asientos de caja menor (guía P11), resueltos contra el plan de la empresa.
"""
from decimal import Decimal


def _c(plan, rol):
    from causacion.plan_cuentas import CUENTAS_ESTANDAR
    return plan.get(rol) or CUENTAS_ESTANDAR[rol]


def _renglon(cuenta_nombre, debito=Decimal("0"), credito=Decimal("0")):
    return {"cuenta": cuenta_nombre[0], "nombre": cuenta_nombre[1],
            "debito": str(debito), "credito": str(credito)}


def asiento_reembolso(reembolso, gastos, plan):
    """Legaliza los vales: débito a cada cuenta de gasto (agrupada) + IVA
    descontable, crédito a bancos por el total. → (renglones, explicación)."""
    por_cuenta = {}
    iva_total = Decimal("0")
    for gasto in gastos:
        cuenta = _c(plan, gasto.categoria)
        por_cuenta[cuenta] = por_cuenta.get(cuenta, Decimal("0")) + gasto.base
        iva_total += gasto.iva

    renglones = [_renglon(cuenta, debito=monto) for cuenta, monto in por_cuenta.items()]
    if iva_total > 0:
        renglones.append(_renglon(_c(plan, "iva_descontable"), debito=iva_total))
    total = sum(g.total for g in gastos)
    renglones.append(_renglon(_c(plan, "bancos"), credito=total))

    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        raise ValueError(f"Asiento de reembolso desbalanceado: {debitos} ≠ {creditos}.")

    explicacion = (
        f"Reembolso de caja menor «{reembolso.caja.nombre}»: se legalizan "
        f"{len(gastos)} vale(s) por ${total:,.0f}. Débito a las cuentas de gasto "
        "y al IVA descontable; crédito a bancos para reponer el fondo a su monto fijo."
    )
    return renglones, explicacion


def asiento_constitucion(caja, plan):
    """Asiento informativo de la constitución del fondo: débito caja menor,
    crédito bancos."""
    return [
        _renglon(_c(plan, "caja_menor"), debito=caja.monto_fijo),
        _renglon(_c(plan, "bancos"), credito=caja.monto_fijo),
    ]
