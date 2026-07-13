"""
Categorías de activos fijos con vida útil y cuentas PUC (guía P10).

Vidas útiles contables comunes en Colombia. La depreciación fiscal puede
diferir; para el certificado NIIF se usaría la vida útil real estimada del
activo — aquí se ofrece un valor por defecto editable por activo.
"""
CATEGORIAS = {
    "edificaciones": {
        "nombre": "Construcciones y edificaciones",
        "vida_anios": 20,
        "cuenta_activo": ("1516", "Construcciones y edificaciones"),
        "cuenta_dep_acum": ("159205", "Depreciación acumulada — construcciones"),
        "cuenta_gasto": ("516005", "Gasto depreciación — construcciones"),
    },
    "maquinaria": {
        "nombre": "Maquinaria y equipo",
        "vida_anios": 10,
        "cuenta_activo": ("1520", "Maquinaria y equipo"),
        "cuenta_dep_acum": ("159210", "Depreciación acumulada — maquinaria"),
        "cuenta_gasto": ("516010", "Gasto depreciación — maquinaria"),
    },
    "equipo_oficina": {
        "nombre": "Equipo de oficina, muebles y enseres",
        "vida_anios": 10,
        "cuenta_activo": ("1524", "Equipo de oficina"),
        "cuenta_dep_acum": ("159215", "Depreciación acumulada — equipo de oficina"),
        "cuenta_gasto": ("516015", "Gasto depreciación — equipo de oficina"),
    },
    "equipo_computo": {
        "nombre": "Equipo de cómputo y comunicación",
        "vida_anios": 5,
        "cuenta_activo": ("1528", "Equipo de cómputo y comunicación"),
        "cuenta_dep_acum": ("159220", "Depreciación acumulada — cómputo"),
        "cuenta_gasto": ("516020", "Gasto depreciación — cómputo"),
    },
    "vehiculos": {
        "nombre": "Flota y equipo de transporte",
        "vida_anios": 5,
        "cuenta_activo": ("1540", "Flota y equipo de transporte"),
        "cuenta_dep_acum": ("159225", "Depreciación acumulada — transporte"),
        "cuenta_gasto": ("516025", "Gasto depreciación — transporte"),
    },
}


def vida_util_meses(categoria):
    return CATEGORIAS[categoria]["vida_anios"] * 12
