"""
Plan de cuentas por empresa (consolidación multi-empresa).

Cada asiento de la app se arma con "roles de cuenta" (claves semánticas
estables), no con números PUC quemados. El catálogo CUENTAS_ESTANDAR da el
valor por defecto (PUC colombiano común); cada empresa puede sobreescribir
el código y el nombre de cualquier rol en su propio plan (modelo
CuentaContable), para calzar con el plan de cuentas de SU software contable.

Los motores llaman plan_de_empresa(empresa) una vez y resuelven cada rol
contra ese dict.
"""

# rol -> (código PUC por defecto, nombre por defecto). Un solo lugar de verdad.
CUENTAS_ESTANDAR = {
    # --- Causación de compras ---
    "iva_descontable": ("240802", "IVA descontable"),
    "proveedores": ("2205", "Proveedores nacionales"),
    "costos_gastos_por_pagar": ("2335", "Costos y gastos por pagar"),
    "retefuente_honorarios": ("236515", "Retención en la fuente — honorarios"),
    "retefuente_servicios": ("236525", "Retención en la fuente — servicios"),
    "retefuente_compras": ("236540", "Retención en la fuente — compras"),
    "retefuente_arrendamiento": ("236530", "Retención en la fuente — arrendamientos"),
    # --- Clasificación PUC del gasto/activo (reglas) ---
    "gasto_honorarios": ("5110", "Honorarios"),
    "inventario_mercancias": ("1435", "Mercancías no fabricadas por la empresa"),
    "gasto_aseo_vigilancia": ("5135", "Servicios — aseo y vigilancia"),
    "gasto_mantenimiento": ("5145", "Mantenimiento y reparaciones"),
    "gasto_arrendamiento": ("5120", "Arrendamientos"),
    "ppe_equipo_oficina": ("1524", "Propiedad, planta y equipo — equipo de oficina"),
    "gasto_diversos": ("5195", "Gastos diversos"),
    # --- Ventas ---
    "clientes": ("1305", "Clientes nacionales"),
    "ingresos": ("4135", "Ingresos por ventas y servicios"),
    "iva_generado": ("240801", "IVA generado por pagar"),
    "retefuente_a_favor": ("135515", "Anticipo de impuestos — retefuente a favor"),
    # --- Conciliación bancaria ---
    "bancos": ("111005", "Bancos — moneda nacional"),
    "gmf": ("531595", "Gravamen a los movimientos financieros (GMF)"),
    "comisiones_bancarias": ("530505", "Gastos bancarios — comisiones"),
    # --- Nómina ---
    "nomina_sueldos": ("510506", "Sueldos"),
    "nomina_auxilio": ("510527", "Auxilio de transporte"),
    "nomina_aportes": ("510569", "Aportes seguridad social y parafiscales"),
    "nomina_prestaciones": ("510530", "Prestaciones sociales (provisión del mes)"),
    "nomina_salarios_por_pagar": ("250505", "Salarios por pagar"),
    "nomina_aportes_por_pagar": ("237005", "Aportes y retenciones de nómina por pagar"),
    "nomina_descuentos": ("237010", "Descuentos de nómina por pagar (préstamos, embargos)"),
    "nomina_provisiones": ("261005", "Provisión prestaciones sociales"),
    # --- Activos fijos: activo / depreciación acumulada / gasto, por categoría ---
    "activo_edificaciones": ("1516", "Construcciones y edificaciones"),
    "depacum_edificaciones": ("159205", "Depreciación acumulada — construcciones"),
    "gastodep_edificaciones": ("516005", "Gasto depreciación — construcciones"),
    "activo_maquinaria": ("1520", "Maquinaria y equipo"),
    "depacum_maquinaria": ("159210", "Depreciación acumulada — maquinaria"),
    "gastodep_maquinaria": ("516010", "Gasto depreciación — maquinaria"),
    "activo_equipo_oficina": ("1524", "Equipo de oficina"),
    "depacum_equipo_oficina": ("159215", "Depreciación acumulada — equipo de oficina"),
    "gastodep_equipo_oficina": ("516015", "Gasto depreciación — equipo de oficina"),
    "activo_equipo_computo": ("1528", "Equipo de cómputo y comunicación"),
    "depacum_equipo_computo": ("159220", "Depreciación acumulada — cómputo"),
    "gastodep_equipo_computo": ("516020", "Gasto depreciación — cómputo"),
    "activo_vehiculos": ("1540", "Flota y equipo de transporte"),
    "depacum_vehiculos": ("159225", "Depreciación acumulada — transporte"),
    "gastodep_vehiculos": ("516025", "Gasto depreciación — transporte"),
    # --- Caja menor ---
    "caja_menor": ("110505", "Caja menor"),
    "cm_papeleria": ("519530", "Útiles, papelería y fotocopias"),
    "cm_transporte": ("519525", "Combustibles, transporte y acarreos"),
    "cm_cafeteria": ("519545", "Cafetería, aseo y elementos"),
    "cm_otros": ("519595", "Otros gastos diversos de caja menor"),
}

# Agrupación para mostrar el plan ordenado en la UI
GRUPOS = [
    ("Compras", ["iva_descontable", "proveedores", "costos_gastos_por_pagar",
                 "retefuente_honorarios", "retefuente_servicios",
                 "retefuente_compras", "retefuente_arrendamiento"]),
    ("Clasificación del gasto/activo", [
        "gasto_honorarios", "inventario_mercancias", "gasto_aseo_vigilancia",
        "gasto_mantenimiento", "gasto_arrendamiento", "ppe_equipo_oficina",
        "gasto_diversos"]),
    ("Ventas", ["clientes", "ingresos", "iva_generado", "retefuente_a_favor"]),
    ("Bancos", ["bancos", "gmf", "comisiones_bancarias"]),
    ("Nómina", ["nomina_sueldos", "nomina_auxilio", "nomina_aportes",
                "nomina_prestaciones", "nomina_salarios_por_pagar",
                "nomina_aportes_por_pagar", "nomina_descuentos", "nomina_provisiones"]),
    ("Activos fijos", [
        "activo_edificaciones", "depacum_edificaciones", "gastodep_edificaciones",
        "activo_maquinaria", "depacum_maquinaria", "gastodep_maquinaria",
        "activo_equipo_oficina", "depacum_equipo_oficina", "gastodep_equipo_oficina",
        "activo_equipo_computo", "depacum_equipo_computo", "gastodep_equipo_computo",
        "activo_vehiculos", "depacum_vehiculos", "gastodep_vehiculos"]),
    ("Caja menor", ["caja_menor", "cm_papeleria", "cm_transporte",
                    "cm_cafeteria", "cm_otros"]),
]

# Categorías de gasto ofrecidas al registrar un vale de caja menor (rol → etiqueta)
CATEGORIAS_CAJA_MENOR = [
    ("cm_papeleria", "Papelería y fotocopias"),
    ("cm_transporte", "Transporte y combustible"),
    ("cm_cafeteria", "Cafetería y aseo"),
    ("cm_otros", "Otros gastos menores"),
]


def plan_de_empresa(empresa):
    """dict rol -> (código, nombre): el estándar con las personalizaciones de
    la empresa encima. Un solo query, se pasa a los motores."""
    from .models import CuentaContable
    plan = dict(CUENTAS_ESTANDAR)
    if empresa is not None:
        for cuenta in CuentaContable.objects.filter(empresa=empresa):
            if cuenta.rol in plan:
                plan[cuenta.rol] = (cuenta.codigo, cuenta.nombre)
    return plan
