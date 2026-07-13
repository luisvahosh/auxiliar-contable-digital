"""
Parámetros tributarios del motor de causación.

Son datos de dominio (no configuración de despliegue, PLAN.md §4): viven en
código con su fuente documentada. Meta futura: tabla administrable con
actualización anual de UVT y tarifas (guía P3).
"""
from decimal import Decimal

# UVT por año — fuente: resolución DIAN de noviembre de cada año.
# OJO: confirmar el valor 2026 contra la resolución oficial antes de usar en
# producción; los cálculos de base mínima dependen de esto.
UVT = {
    2025: Decimal("49799"),
    2026: Decimal("52374"),
}


def uvt_del_anio(anio):
    """UVT del año fiscal pedido; si no está cargado, el último conocido anterior."""
    if anio in UVT:
        return UVT[anio]
    anteriores = [a for a in UVT if a < anio]
    if not anteriores:
        raise ValueError(f"No hay valor de UVT cargado para {anio} ni años anteriores.")
    return UVT[max(anteriores)]


# Conceptos de retención en la fuente a título de renta.
# La calidad real del tercero (declarante, autorretenedor, RST) sale de la
# matriz de terceros (guía P3), alimentada del RUT; si el tercero aún no está
# verificado, se asume declarante y la explicación lo advierte.
CONCEPTOS_RETENCION = {
    "honorarios": {
        "nombre": "Honorarios y comisiones",
        "base_uvt": Decimal("0"),
        "tarifa_persona_natural": Decimal("10"),
        "tarifa_persona_juridica": Decimal("11"),
        "tarifa_no_declarante": Decimal("10"),
        "rol_cuenta": "retefuente_honorarios",
    },
    "servicios": {
        "nombre": "Servicios generales",
        "base_uvt": Decimal("4"),
        "tarifa_persona_natural": Decimal("4"),
        "tarifa_persona_juridica": Decimal("4"),
        "tarifa_no_declarante": Decimal("6"),
        "rol_cuenta": "retefuente_servicios",
    },
    "compras": {
        "nombre": "Compras generales",
        "base_uvt": Decimal("27"),
        "tarifa_persona_natural": Decimal("2.5"),
        "tarifa_persona_juridica": Decimal("2.5"),
        "tarifa_no_declarante": Decimal("3.5"),
        "rol_cuenta": "retefuente_compras",
    },
    "arrendamiento_inmueble": {
        "nombre": "Arrendamiento de bienes inmuebles",
        "base_uvt": Decimal("27"),
        "tarifa_persona_natural": Decimal("3.5"),
        "tarifa_persona_juridica": Decimal("3.5"),
        "tarifa_no_declarante": Decimal("3.5"),
        "rol_cuenta": "retefuente_arrendamiento",
    },
}

# Responsabilidades fiscales (TaxLevelCode del XML) que eximen de retefuente.
RESPONSABILIDADES_SIN_RETENCION = {
    "O-47": "El proveedor pertenece al Régimen Simple de Tributación: no es "
            "sujeto de retención en la fuente a título de renta (art. 911 E.T.).",
    "O-15": "El proveedor es autorretenedor según su RUT: él mismo practica su "
            "retención; el comprador no retiene.",
}

# Las cuentas PUC del asiento ya no viven aquí: son roles resueltos contra el
# plan de cuentas de cada empresa (plan_cuentas.CUENTAS_ESTANDAR + overrides).
