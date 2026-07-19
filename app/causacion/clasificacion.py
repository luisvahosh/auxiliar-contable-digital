"""
Motor de clasificación PUC y retención en la fuente — reglas explícitas.

Las reglas apuntan a ROLES de cuenta (gasto_honorarios, inventario_mercancias,
…); el código y nombre concretos se resuelven contra el plan de cuentas de la
empresa (plan_cuentas.plan_de_empresa) — así cada empresa usa SUS cuentas.

Humano en el circuito (CLAUDE.md §3): toda propuesta lleva nivel
(automática/sugerida) y su porqué; nada se contabiliza sin aprobación.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from .parametros import (
    CONCEPTOS_RETENCION,
    RESPONSABILIDADES_SIN_RETENCION,
    uvt_del_anio,
)
from .plan_cuentas import CUENTAS_ESTANDAR

# (patrón sobre nota+líneas en minúsculas, rol de cuenta, concepto de retención)
REGLAS_PUC = [
    (r"honorario|asesor[ií]a|consultor[ií]a", "gasto_honorarios", "honorarios"),
    (r"mercanc[ií]a", "inventario_mercancias", "compras"),
    (r"aseo|cafeter[ií]a|vigilancia|limpieza", "gasto_aseo_vigilancia", "servicios"),
    (r"mantenimiento|reparaci[oó]n", "gasto_mantenimiento", "servicios"),
    (r"instalaci[oó]n|adecuaci[oó]n", "gasto_mantenimiento", "servicios"),
    (r"arrendamiento|alquiler|canon", "gasto_arrendamiento", "arrendamiento_inmueble"),
    (r"aire acondicionado|computador|servidor|maquinaria|veh[ií]culo",
     "ppe_equipo_oficina", "compras"),
]

ROL_SIN_REGLA = ("gasto_diversos", "servicios")


def _cuenta(plan, rol):
    """(código, nombre) del rol en el plan (o el estándar como respaldo)."""
    return plan.get(rol) or CUENTAS_ESTANDAR[rol]


def cuentas_reclasificables(plan):
    """Cuentas elegibles al reclasificar a mano: las de las reglas + comodín.
    → [(código, nombre, concepto, rol)] con los valores del plan de la empresa."""
    vistas = {}
    for _, rol, concepto in REGLAS_PUC:
        codigo, nombre = _cuenta(plan, rol)
        vistas.setdefault(codigo, (codigo, nombre, concepto, rol))
    codigo, nombre = _cuenta(plan, ROL_SIN_REGLA[0])
    vistas.setdefault(codigo, (codigo, nombre, ROL_SIN_REGLA[1], ROL_SIN_REGLA[0]))
    return sorted(vistas.values())


@dataclass
class Propuesta:
    cuenta: str
    nombre_cuenta: str
    concepto: str
    nivel: str            # "automatica" | "sugerida"
    explicacion: str
    rol: str = ""         # rol de cuenta (para elegir la contrapartida)
    candidatas: list = field(default_factory=list)


@dataclass
class Retencion:
    valor: Decimal
    tarifa: Decimal | None
    cuenta: str
    nombre_cuenta: str
    porque: str


def clasificar(factura, plan, tercero=None):
    """Propone la cuenta PUC del gasto/activo y el concepto de retención.

    Si el contador ya le fijó una regla al tercero (memoria por tercero — su
    retroalimentación: "a este proveedor cáusalo siempre por servicios en tal
    cuenta"), esa regla MANDA sobre lo que adivine el texto. Si no, se clasifica
    por el texto de la factura como siempre."""
    if tercero is not None and tercero.concepto_retencion:
        return _clasificar_por_tercero(factura, plan, tercero)
    return _clasificar_por_texto(factura, plan)


def _clasificar_por_tercero(factura, plan, tercero):
    """Regla fija que el contador amarró al proveedor."""
    concepto = tercero.concepto_retencion
    nombre_concepto = CONCEPTOS_RETENCION[concepto]["nombre"]
    if tercero.cuenta_gasto:
        codigo, nombre = tercero.cuenta_gasto, (tercero.nombre_cuenta_gasto
                                                or f"Cuenta {tercero.cuenta_gasto}")
        detalle_cuenta = f"cuenta {codigo} ({nombre}) fijada para este proveedor"
    else:
        # El contador fijó el concepto pero no la cuenta: se propone por el texto.
        base = _clasificar_por_texto(factura, plan)
        codigo, nombre = base.cuenta, base.nombre_cuenta
        detalle_cuenta = f"cuenta {codigo} ({nombre}) propuesta por el texto"
    return Propuesta(
        codigo, nombre, concepto, "automatica",
        f"Regla del contador para {tercero.razon_social}: causar por "
        f"{nombre_concepto} — {detalle_cuenta}. (Puedes reclasificar si este "
        "documento es una excepción.)",
        rol="",
    )


def _clasificar_por_texto(factura, plan):
    """Propone la cuenta PUC del gasto/activo a partir del texto de la factura,
    usando el plan de cuentas de la empresa."""
    texto = factura.texto_clasificable
    coincidencias = []  # (rol, código, nombre, concepto, palabra)
    roles_vistos = set()
    for patron, rol, concepto in REGLAS_PUC:
        encontrado = re.search(patron, texto)
        if encontrado and rol not in roles_vistos:
            roles_vistos.add(rol)
            codigo, nombre = _cuenta(plan, rol)
            coincidencias.append((rol, codigo, nombre, concepto, encontrado.group(0)))

    if not coincidencias:
        codigo, nombre = _cuenta(plan, ROL_SIN_REGLA[0])
        return Propuesta(
            codigo, nombre, ROL_SIN_REGLA[1], "sugerida",
            "Ninguna regla reconoció el concepto de la factura. Se propone "
            f"{codigo} ({nombre}) como comodín: revisar y reclasificar antes de aprobar.",
            rol=ROL_SIN_REGLA[0],
        )

    if len(coincidencias) == 1:
        rol, codigo, nombre, concepto, palabra = coincidencias[0]
        return Propuesta(
            codigo, nombre, concepto, "automatica",
            f"El texto de la factura menciona «{palabra}» → cuenta {codigo} ({nombre}), "
            f"concepto de retención: {CONCEPTOS_RETENCION[concepto]['nombre']}.",
            rol=rol,
        )

    rol, codigo, nombre, concepto, _ = coincidencias[0]
    opciones = "; ".join(f"{c} ({n}, por «{p}»)" for _, c, n, _, p in coincidencias)
    return Propuesta(
        codigo, nombre, concepto, "sugerida",
        f"El concepto es ambiguo — admite más de una cuenta PUC: {opciones}. "
        "La decisión (¿activo que se capitaliza o gasto del período?) cambia el "
        "asiento y la tarifa de retención; requiere revisión humana.",
        rol=rol,
        candidatas=[{"cuenta": c, "nombre": n} for _, c, n, _, _ in coincidencias],
    )


def calcular_retencion(factura, concepto, tercero=None, plan=None):
    """Retefuente a practicar según la calidad del proveedor, base mínima y tarifa.

    Si hay tercero (matriz de terceros, P3), su calidad manda sobre el XML;
    sin tercero se lee el TaxLevelCode del XML y se asume declarante. La cuenta
    de retención se resuelve contra el plan de la empresa."""
    plan = plan or dict(CUENTAS_ESTANDAR)
    if tercero is not None:
        origen = ("la matriz de terceros" if tercero.verificado
                  else "la matriz de terceros (pendiente de verificar contra el RUT)")
        es_rst = tercero.regimen_simple
        es_autorretenedor = tercero.autorretenedor
        declarante = tercero.declarante
        es_natural = tercero.tipo_persona == "2"
    else:
        origen = "el XML de la factura"
        es_rst = factura.responsabilidad_emisor == "O-47"
        es_autorretenedor = factura.responsabilidad_emisor == "O-15"
        declarante = True
        es_natural = factura.tipo_persona_emisor == "2"

    if es_rst:
        return Retencion(Decimal("0"), None, "", "",
                         f"{RESPONSABILIDADES_SIN_RETENCION['O-47']} Fuente: {origen}.")
    if es_autorretenedor:
        return Retencion(Decimal("0"), None, "", "",
                         f"{RESPONSABILIDADES_SIN_RETENCION['O-15']} Fuente: {origen}.")

    datos = CONCEPTOS_RETENCION[concepto]
    anio = factura.fecha_emision.year
    uvt = uvt_del_anio(anio)
    base_minima = (datos["base_uvt"] * uvt).quantize(Decimal("1"))
    if factura.subtotal < base_minima:
        return Retencion(
            Decimal("0"), None, "", "",
            f"No aplica retención: la base (${factura.subtotal:,.0f}) es menor que "
            f"la base mínima de {datos['base_uvt']} UVT para {datos['nombre'].lower()} "
            f"(${base_minima:,.0f} en {anio}).",
        )

    if not declarante:
        tarifa = datos["tarifa_no_declarante"]
        calidad = "no declarante"
    elif es_natural:
        tarifa = datos["tarifa_persona_natural"]
        calidad = "persona natural declarante"
    else:
        tarifa = datos["tarifa_persona_juridica"]
        calidad = "persona jurídica declarante"
    valor = (factura.subtotal * tarifa / 100).quantize(Decimal("1"))
    codigo, nombre = plan.get(datos["rol_cuenta"]) or CUENTAS_ESTANDAR[datos["rol_cuenta"]]
    return Retencion(
        valor, tarifa, codigo, nombre,
        f"Retefuente por {datos['nombre'].lower()}: {tarifa}% sobre "
        f"${factura.subtotal:,.0f} = ${valor:,.0f} ({calidad}, según {origen}).",
    )


def construir_asiento(factura, propuesta, retencion, plan):
    """Renglones del asiento de causación (partida doble). Los montos van como
    texto para guardarse en JSON sin perder precisión decimal."""
    renglones = []

    def renglon(cuenta, nombre, debito=Decimal("0"), credito=Decimal("0")):
        renglones.append({
            "cuenta": cuenta, "nombre": nombre,
            "debito": str(debito), "credito": str(credito),
        })

    renglon(propuesta.cuenta, propuesta.nombre_cuenta, debito=factura.subtotal)
    if factura.iva > 0:
        renglon(*_cuenta(plan, "iva_descontable"), debito=factura.iva)
    if retencion.valor > 0:
        renglon(retencion.cuenta, retencion.nombre_cuenta, credito=retencion.valor)
    # La compra de inventario se debe a proveedores; el resto, a costos y gastos.
    rol_contrapartida = ("proveedores" if propuesta.rol == "inventario_mercancias"
                         else "costos_gastos_por_pagar")
    renglon(*_cuenta(plan, rol_contrapartida), credito=factura.total - retencion.valor)

    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        # Control del auxiliar: jamás persistir un asiento desbalanceado.
        raise ValueError(f"Asiento desbalanceado: débitos {debitos} ≠ créditos {creditos}.")
    return renglones


def construir_asiento_nota_credito_compra(nota, original, plan):
    """Reversa (parcial o total) de una compra ya causada: se descarga la
    cuenta por pagar y se acreditan el gasto/activo y el IVA descontable.
    Devuelve (renglones, explicación)."""
    renglones = []

    def renglon(cuenta, nombre, debito=Decimal("0"), credito=Decimal("0")):
        renglones.append({"cuenta": cuenta, "nombre": nombre,
                          "debito": str(debito), "credito": str(credito)})

    # La contrapartida del pago es la misma cuenta por pagar del asiento original
    por_pagar = next(
        (r for r in original.asiento
         if Decimal(r["credito"]) > 0 and r["cuenta"].startswith("2")
         and not r["cuenta"].startswith("2365")),
        {"cuenta": _cuenta(plan, "costos_gastos_por_pagar")[0],
         "nombre": _cuenta(plan, "costos_gastos_por_pagar")[1]},
    )
    renglon(por_pagar["cuenta"], por_pagar["nombre"], debito=nota.total)
    renglon(original.cuenta_puc, original.nombre_cuenta_puc, credito=nota.subtotal)
    if nota.iva > 0:
        renglon(*_cuenta(plan, "iva_descontable"), credito=nota.iva)

    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        raise ValueError(f"Asiento desbalanceado: débitos {debitos} ≠ créditos {creditos}.")

    alcance = "total" if nota.total == original.total else "parcial"
    explicacion = (
        f"Nota crédito de proveedor {nota.numero}: reversa {alcance} de la compra "
        f"{original.numero} (${nota.total:,.0f} de ${original.total:,.0f}). Se descarga "
        f"la cuenta por pagar y se acreditan {original.cuenta_puc} y el IVA descontable."
    )
    if original.retencion > 0:
        explicacion += (" OJO: la compra original tuvo retefuente — si la declaración "
                        "del período no se ha presentado, revisar el ajuste de la retención.")
    return renglones, explicacion
