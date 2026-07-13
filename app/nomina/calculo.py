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


def _resumen_novedades(novedades):
    """Suma las novedades por efecto. → (constitutivo, no_constitutivo,
    reduce_base, descuento)."""
    from .models import EFECTO_NOVEDAD
    totales = {"constitutivo": Decimal("0"), "no_constitutivo": Decimal("0"),
               "reduce_base": Decimal("0"), "descuento": Decimal("0")}
    for novedad in novedades:
        efecto = EFECTO_NOVEDAD[novedad.tipo][1]
        totales[efecto] += novedad.valor
    return totales


def liquidar_empleado(empleado, valores, exonerada, novedades=()):
    """Liquidación del mes para un empleado, aplicando sus novedades (P8.8).
    → dict con todos los rubros."""
    smmlv = valores["smmlv"]
    nov = _resumen_novedades(novedades)

    # Base salarial del mes = salario + devengos constitutivos − días no trabajados.
    # Sobre ella se calculan deducciones, aportes y provisiones (salvo auxilio).
    salario_base = empleado.salario + nov["constitutivo"] - nov["reduce_base"]
    if salario_base < 0:
        salario_base = Decimal("0")

    # El auxilio de transporte se define por el salario contratado, no por la base.
    auxilio = valores["auxilio_transporte"] if empleado.salario <= 2 * smmlv else Decimal("0")
    devengado = salario_base + auxilio + nov["no_constitutivo"]

    salud_empleado = _al_peso(salario_base * p.SALUD_EMPLEADO)
    pension_empleado = _al_peso(salario_base * p.PENSION_EMPLEADO)
    deducciones = salud_empleado + pension_empleado + nov["descuento"]
    neto = devengado - deducciones

    # Exoneración art. 114-1 E.T.: salud patronal, SENA e ICBF no se pagan
    # para salarios < 10 SMMLV si la empresa es beneficiaria.
    paga_plenos = (not exonerada) or empleado.salario >= 10 * smmlv
    aportes = {
        "pension": _al_peso(salario_base * p.PENSION_EMPLEADOR),
        "salud": _al_peso(salario_base * p.SALUD_EMPLEADOR) if paga_plenos else Decimal("0"),
        "arl": _al_peso(salario_base * p.ARL_NIVEL_1),
        "caja": _al_peso(salario_base * p.CAJA_COMPENSACION),
        "sena": _al_peso(salario_base * p.SENA) if paga_plenos else Decimal("0"),
        "icbf": _al_peso(salario_base * p.ICBF) if paga_plenos else Decimal("0"),
    }
    base_prestaciones = salario_base + auxilio  # el auxilio sí es base de prestaciones
    provisiones = {
        "cesantias": _al_peso(base_prestaciones * p.CESANTIAS),
        "intereses": _al_peso(base_prestaciones * p.INTERESES_CESANTIAS),
        "prima": _al_peso(base_prestaciones * p.PRIMA),
        "vacaciones": _al_peso(salario_base * p.VACACIONES),
    }

    return {
        "empleado": empleado.nombre,
        "cedula": empleado.cedula,
        "salario": str(empleado.salario),
        "novedades_devengo": str(nov["constitutivo"] + nov["no_constitutivo"]),
        "novedades_descuento": str(nov["descuento"] + nov["reduce_base"]),
        "auxilio": str(auxilio),
        "devengado": str(devengado),
        # IBC (base de cotización a seguridad social): el salario base, sin auxilio.
        "ibc": str(salario_base),
        "salud_empleado": str(salud_empleado),
        "pension_empleado": str(pension_empleado),
        "otros_descuentos": str(nov["descuento"]),
        "neto": str(neto),
        # Desglose de aportes patronales, insumo de la pre-PILA (P8.9).
        "aportes": {rol: str(valor) for rol, valor in aportes.items()},
        "aportes_empleador": str(sum(aportes.values())),
        "provisiones": str(sum(provisiones.values())),
    }


def liquidar_mes(empresa, empleados, anio, mes, novedades_por_empleado=None):
    """Liquidación consolidada del mes: detalle por empleado, totales,
    asiento balanceado y explicación."""
    valores = p.parametros_del_anio(anio)
    exonerada = empresa.exonerada_parafiscales
    novedades_por_empleado = novedades_por_empleado or {}

    detalle = [
        liquidar_empleado(e, valores, exonerada,
                          novedades_por_empleado.get(e.pk, []))
        for e in empleados
    ]

    def suma(campo):
        return sum(Decimal(fila[campo]) for fila in detalle)

    auxilios = suma("auxilio")
    sueldos = suma("devengado") - auxilios          # gasto de sueldos (incluye novedades)
    deducciones_seg = suma("salud_empleado") + suma("pension_empleado")
    otros_descuentos = suma("otros_descuentos")
    neto = suma("neto")
    aportes = suma("aportes_empleador")
    provisiones = suma("provisiones")

    from causacion.plan_cuentas import CUENTAS_ESTANDAR, plan_de_empresa
    plan = plan_de_empresa(empresa)

    def cta(rol):
        return plan.get(rol) or CUENTAS_ESTANDAR[rol]

    renglones = []

    def renglon(cuenta_nombre, debito=Decimal("0"), credito=Decimal("0")):
        if debito == 0 and credito == 0:
            return
        renglones.append({"cuenta": cuenta_nombre[0], "nombre": cuenta_nombre[1],
                          "debito": str(debito), "credito": str(credito)})

    renglon(cta("nomina_sueldos"), debito=sueldos)
    renglon(cta("nomina_auxilio"), debito=auxilios)
    renglon(cta("nomina_aportes"), debito=aportes)
    renglon(cta("nomina_prestaciones"), debito=provisiones)
    renglon(cta("nomina_salarios_por_pagar"), credito=neto)
    renglon(cta("nomina_aportes_por_pagar"), credito=deducciones_seg + aportes)
    renglon(cta("nomina_descuentos"), credito=otros_descuentos)
    renglon(cta("nomina_provisiones"), credito=provisiones)

    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        raise ValueError(f"Asiento de nómina desbalanceado: {debitos} ≠ {creditos}.")

    hay_novedades = any(novedades_por_empleado.values())
    explicacion = (
        f"Liquidación {anio}-{mes:02d} de {len(detalle)} empleado(s) con SMMLV "
        f"${valores['smmlv']:,.0f} y auxilio ${valores['auxilio_transporte']:,.0f} "
        f"(VERIFICAR contra decretos del año). Deducciones del empleado: salud 4% y "
        f"pensión 4%. Empresa {'EXONERADA' if exonerada else 'NO exonerada'} de salud "
        "patronal, SENA e ICBF (art. 114-1 E.T.) para salarios < 10 SMMLV. "
        "Provisiones: cesantías 8.33%, intereses 1%, prima 8.33% y vacaciones 4.17%. "
        + ("Con novedades del mes (horas extra, bonos, descuentos): los devengos "
           "constitutivos y los días no laborados ajustan la base de aportes y "
           "provisiones." if hay_novedades else "Sin novedades: mes completo para todos.")
    )

    return {
        "detalle": detalle,
        "totales": {
            "devengado": sueldos + auxilios,
            "deducciones": deducciones_seg + otros_descuentos,
            "neto": neto,
            "aportes_empleador": aportes,
            "provisiones": provisiones,
        },
        "asiento": renglones,
        "explicacion": explicacion,
    }
