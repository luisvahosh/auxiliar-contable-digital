"""
Motor de liquidación mensual de nómina (guía P8) — núcleo sin novedades:
salario fijo mes completo. Horas extra, incapacidades y retiros llegan en
la siguiente iteración; PILA y nómina electrónica las presenta el humano.

Todo en Decimal redondeado al peso; el asiento consolidado del mes debe
balancear al centavo o se aborta.
"""
from decimal import ROUND_HALF_UP, Decimal

from . import parametros as p

PESO = Decimal("1")


def _al_peso(valor):
    return valor.quantize(PESO, rounding=ROUND_HALF_UP)


def liquidar_empleado(empleado, valores, exonerada):
    """Liquidación del mes para un empleado. → dict con todos los rubros."""
    salario = empleado.salario
    smmlv = valores["smmlv"]
    auxilio = valores["auxilio_transporte"] if salario <= 2 * smmlv else Decimal("0")
    devengado = salario + auxilio

    salud_empleado = _al_peso(salario * p.SALUD_EMPLEADO)
    pension_empleado = _al_peso(salario * p.PENSION_EMPLEADO)
    deducciones = salud_empleado + pension_empleado
    neto = devengado - deducciones

    # Exoneración art. 114-1 E.T.: salud patronal, SENA e ICBF no se pagan
    # para salarios < 10 SMMLV si la empresa es beneficiaria.
    paga_plenos = (not exonerada) or salario >= 10 * smmlv
    aportes = {
        "pension": _al_peso(salario * p.PENSION_EMPLEADOR),
        "salud": _al_peso(salario * p.SALUD_EMPLEADOR) if paga_plenos else Decimal("0"),
        "arl": _al_peso(salario * p.ARL_NIVEL_1),
        "caja": _al_peso(salario * p.CAJA_COMPENSACION),
        "sena": _al_peso(salario * p.SENA) if paga_plenos else Decimal("0"),
        "icbf": _al_peso(salario * p.ICBF) if paga_plenos else Decimal("0"),
    }
    provisiones = {
        "cesantias": _al_peso(devengado * p.CESANTIAS),
        "intereses": _al_peso(devengado * p.INTERESES_CESANTIAS),
        "prima": _al_peso(devengado * p.PRIMA),
        "vacaciones": _al_peso(salario * p.VACACIONES),
    }

    return {
        "empleado": empleado.nombre,
        "cedula": empleado.cedula,
        "salario": str(salario),
        "auxilio": str(auxilio),
        "devengado": str(devengado),
        "salud_empleado": str(salud_empleado),
        "pension_empleado": str(pension_empleado),
        "neto": str(neto),
        "aportes_empleador": str(sum(aportes.values())),
        "provisiones": str(sum(provisiones.values())),
    }


def liquidar_mes(empresa, empleados, anio, mes):
    """Liquidación consolidada del mes: detalle por empleado, totales,
    asiento balanceado y explicación."""
    valores = p.parametros_del_anio(anio)
    exonerada = empresa.exonerada_parafiscales

    detalle = [liquidar_empleado(e, valores, exonerada) for e in empleados]

    def suma(campo):
        return sum(Decimal(fila[campo]) for fila in detalle)

    salarios = suma("salario")
    auxilios = suma("auxilio")
    deducciones = suma("salud_empleado") + suma("pension_empleado")
    neto = suma("neto")
    aportes = suma("aportes_empleador")
    provisiones = suma("provisiones")

    renglones = []

    def renglon(cuenta_nombre, debito=Decimal("0"), credito=Decimal("0")):
        if debito == 0 and credito == 0:
            return
        renglones.append({"cuenta": cuenta_nombre[0], "nombre": cuenta_nombre[1],
                          "debito": str(debito), "credito": str(credito)})

    renglon(p.CUENTA_SUELDOS, debito=salarios)
    renglon(p.CUENTA_AUXILIO, debito=auxilios)
    renglon(p.CUENTA_APORTES, debito=aportes)
    renglon(p.CUENTA_PRESTACIONES, debito=provisiones)
    renglon(p.CUENTA_SALARIOS_POR_PAGAR, credito=neto)
    renglon(p.CUENTA_APORTES_POR_PAGAR, credito=deducciones + aportes)
    renglon(p.CUENTA_PROVISIONES, credito=provisiones)

    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        raise ValueError(f"Asiento de nómina desbalanceado: {debitos} ≠ {creditos}.")

    explicacion = (
        f"Liquidación {anio}-{mes:02d} de {len(detalle)} empleado(s) con SMMLV "
        f"${valores['smmlv']:,.0f} y auxilio ${valores['auxilio_transporte']:,.0f} "
        f"(VERIFICAR contra decretos del año). Deducciones del empleado: salud 4% y "
        f"pensión 4%. Empresa {'EXONERADA' if exonerada else 'NO exonerada'} de salud "
        "patronal, SENA e ICBF (art. 114-1 E.T.) para salarios < 10 SMMLV. "
        "Provisiones: cesantías 8.33%, intereses 1%, prima 8.33% (sobre devengado) "
        "y vacaciones 4.17% (sobre salario). Sin novedades: mes completo para todos."
    )

    return {
        "detalle": detalle,
        "totales": {
            "devengado": salarios + auxilios,
            "deducciones": deducciones,
            "neto": neto,
            "aportes_empleador": aportes,
            "provisiones": provisiones,
        },
        "asiento": renglones,
        "explicacion": explicacion,
    }
