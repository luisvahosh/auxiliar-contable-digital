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
# Tarifas para declarantes: la calidad real del tercero (declarante,
# autorretenedor, RST) saldrá del RUT en la matriz de terceros (guía P3);
# mientras tanto se asume declarante y se dice en la explicación.
CONCEPTOS_RETENCION = {
    "honorarios": {
        "nombre": "Honorarios y comisiones",
        "base_uvt": Decimal("0"),
        "tarifa_persona_natural": Decimal("10"),
        "tarifa_persona_juridica": Decimal("11"),
        "cuenta": "236515",
        "nombre_cuenta": "Retención en la fuente — honorarios",
    },
    "servicios": {
        "nombre": "Servicios generales",
        "base_uvt": Decimal("4"),
        "tarifa_persona_natural": Decimal("4"),
        "tarifa_persona_juridica": Decimal("4"),
        "cuenta": "236525",
        "nombre_cuenta": "Retención en la fuente — servicios",
    },
    "compras": {
        "nombre": "Compras generales",
        "base_uvt": Decimal("27"),
        "tarifa_persona_natural": Decimal("2.5"),
        "tarifa_persona_juridica": Decimal("2.5"),
        "cuenta": "236540",
        "nombre_cuenta": "Retención en la fuente — compras",
    },
    "arrendamiento_inmueble": {
        "nombre": "Arrendamiento de bienes inmuebles",
        "base_uvt": Decimal("27"),
        "tarifa_persona_natural": Decimal("3.5"),
        "tarifa_persona_juridica": Decimal("3.5"),
        "cuenta": "236530",
        "nombre_cuenta": "Retención en la fuente — arrendamientos",
    },
}

# Responsabilidades fiscales (TaxLevelCode del XML) que eximen de retefuente.
RESPONSABILIDADES_SIN_RETENCION = {
    "O-47": "El proveedor pertenece al Régimen Simple de Tributación: no es "
            "sujeto de retención en la fuente a título de renta (art. 911 E.T.).",
    "O-15": "El proveedor es autorretenedor según su RUT: él mismo practica su "
            "retención; el comprador no retiene.",
}

# Cuentas PUC fijas del asiento de causación (compras).
CUENTA_IVA_DESCONTABLE = ("240802", "IVA descontable")
CUENTA_PROVEEDORES = ("2205", "Proveedores nacionales")
CUENTA_COSTOS_GASTOS_POR_PAGAR = ("2335", "Costos y gastos por pagar")

# Cuentas PUC fijas del registro de ventas (P2).
CUENTA_CLIENTES = ("1305", "Clientes nacionales")
CUENTA_INGRESOS = ("4135", "Ingresos por ventas y servicios")
CUENTA_IVA_GENERADO = ("240801", "IVA generado por pagar")
CUENTA_RETEFUENTE_A_FAVOR = ("135515", "Anticipo de impuestos — retefuente a favor")
