"""
Parámetros de nómina por año (guía P8). Datos de dominio con su fuente.

OJO: los valores 2026 son ESTIMADOS — confirmar contra los decretos de
salario mínimo y auxilio de transporte antes de liquidar nómina real.
"""
from decimal import Decimal

PARAMETROS_POR_ANIO = {
    2025: {"smmlv": Decimal("1423500"), "auxilio_transporte": Decimal("200000")},
    # ESTIMADO — confirmar decreto de diciembre 2025:
    2026: {"smmlv": Decimal("1623500"), "auxilio_transporte": Decimal("200000")},
}

# Porcentajes (empleado con contrato laboral ordinario)
SALUD_EMPLEADO = Decimal("0.04")
PENSION_EMPLEADO = Decimal("0.04")

# Aportes del empleador
PENSION_EMPLEADOR = Decimal("0.12")
SALUD_EMPLEADOR = Decimal("0.085")   # solo si no aplica exoneración 114-1
ARL_NIVEL_1 = Decimal("0.00522")     # riesgo I (administrativo); niveles después
CAJA_COMPENSACION = Decimal("0.04")
SENA = Decimal("0.02")               # solo si no aplica exoneración 114-1
ICBF = Decimal("0.03")               # solo si no aplica exoneración 114-1

# Provisiones mensuales de prestaciones
CESANTIAS = Decimal("0.08333")       # sobre devengado (salario + auxilio)
INTERESES_CESANTIAS = Decimal("0.01")  # 12% anual de cesantías ≈ 1% mensual del devengado
PRIMA = Decimal("0.08333")           # sobre devengado
VACACIONES = Decimal("0.0417")       # sobre salario (sin auxilio)


def parametros_del_anio(anio):
    if anio in PARAMETROS_POR_ANIO:
        return PARAMETROS_POR_ANIO[anio]
    anteriores = [a for a in PARAMETROS_POR_ANIO if a < anio]
    if not anteriores:
        raise ValueError(f"No hay parámetros de nómina para {anio}.")
    return PARAMETROS_POR_ANIO[max(anteriores)]


# Cuentas PUC del asiento de nómina (simplificadas a nivel de subcuenta útil)
CUENTA_SUELDOS = ("510506", "Sueldos")
CUENTA_AUXILIO = ("510527", "Auxilio de transporte")
CUENTA_APORTES = ("510569", "Aportes seguridad social y parafiscales")
CUENTA_PRESTACIONES = ("510530", "Prestaciones sociales (provisión del mes)")
CUENTA_SALARIOS_POR_PAGAR = ("250505", "Salarios por pagar")
CUENTA_APORTES_POR_PAGAR = ("237005", "Aportes y retenciones de nómina por pagar")
CUENTA_PROVISIONES = ("261005", "Provisión prestaciones sociales")
