"""
Motor de clasificación PUC y retención en la fuente — reglas explícitas.

Fase actual: reglas deterministas por palabras clave, cada una explicable.
Después (PLAN.md): la IA propone y estas reglas validan y acotan.
Humano en el circuito (CLAUDE.md §3): toda propuesta lleva nivel
(automática/sugerida) y su porqué; nada se contabiliza sin aprobación.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from .parametros import (
    CONCEPTOS_RETENCION,
    CUENTA_COSTOS_GASTOS_POR_PAGAR,
    CUENTA_IVA_DESCONTABLE,
    CUENTA_PROVEEDORES,
    RESPONSABILIDADES_SIN_RETENCION,
    uvt_del_anio,
)

# (patrón sobre nota+líneas en minúsculas, cuenta PUC, nombre de cuenta, concepto de retención)
REGLAS_PUC = [
    (r"honorario|asesor[ií]a|consultor[ií]a", "5110", "Honorarios", "honorarios"),
    (r"mercanc[ií]a", "1435", "Mercancías no fabricadas por la empresa", "compras"),
    (r"aseo|cafeter[ií]a|vigilancia|limpieza", "5135", "Servicios — aseo y vigilancia", "servicios"),
    (r"mantenimiento|reparaci[oó]n", "5145", "Mantenimiento y reparaciones", "servicios"),
    (r"instalaci[oó]n|adecuaci[oó]n", "5145", "Mantenimiento y reparaciones", "servicios"),
    (r"arrendamiento|alquiler|canon", "5120", "Arrendamientos", "arrendamiento_inmueble"),
    (r"aire acondicionado|computador|servidor|maquinaria|veh[ií]culo",
     "1524", "Propiedad, planta y equipo — equipo de oficina", "compras"),
]

CUENTA_SIN_REGLA = ("5195", "Gastos diversos", "servicios")


@dataclass
class Propuesta:
    cuenta: str
    nombre_cuenta: str
    concepto: str
    nivel: str            # "automatica" | "sugerida"
    explicacion: str
    candidatas: list = field(default_factory=list)


@dataclass
class Retencion:
    valor: Decimal
    tarifa: Decimal | None
    cuenta: str
    nombre_cuenta: str
    porque: str


def clasificar(factura):
    """Propone la cuenta PUC del gasto/activo a partir del texto de la factura."""
    texto = factura.texto_clasificable
    coincidencias = []  # (cuenta, nombre, concepto, palabra que disparó)
    for patron, cuenta, nombre, concepto in REGLAS_PUC:
        encontrado = re.search(patron, texto)
        if encontrado and cuenta not in [c[0] for c in coincidencias]:
            coincidencias.append((cuenta, nombre, concepto, encontrado.group(0)))

    if not coincidencias:
        cuenta, nombre, concepto = CUENTA_SIN_REGLA
        return Propuesta(
            cuenta, nombre, concepto, "sugerida",
            "Ninguna regla reconoció el concepto de la factura. Se propone "
            f"{cuenta} ({nombre}) como comodín: revisar y reclasificar antes de aprobar.",
        )

    if len(coincidencias) == 1:
        cuenta, nombre, concepto, palabra = coincidencias[0]
        return Propuesta(
            cuenta, nombre, concepto, "automatica",
            f"El texto de la factura menciona «{palabra}» → cuenta {cuenta} ({nombre}), "
            f"concepto de retención: {CONCEPTOS_RETENCION[concepto]['nombre']}.",
        )

    cuenta, nombre, concepto, _ = coincidencias[0]
    opciones = "; ".join(f"{c} ({n}, por «{p}»)" for c, n, _, p in coincidencias)
    return Propuesta(
        cuenta, nombre, concepto, "sugerida",
        f"El concepto es ambiguo — admite más de una cuenta PUC: {opciones}. "
        "La decisión (¿activo que se capitaliza o gasto del período?) cambia el "
        "asiento y la tarifa de retención; requiere revisión humana.",
        candidatas=[{"cuenta": c, "nombre": n} for c, n, _, _ in coincidencias],
    )


def calcular_retencion(factura, concepto, tercero=None):
    """Retefuente a practicar según la calidad del proveedor, base mínima y tarifa.

    Si hay tercero (matriz de terceros, P3), su calidad manda sobre el XML;
    sin tercero se lee el TaxLevelCode del XML y se asume declarante.
    """
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
    return Retencion(
        valor, tarifa, datos["cuenta"], datos["nombre_cuenta"],
        f"Retefuente por {datos['nombre'].lower()}: {tarifa}% sobre "
        f"${factura.subtotal:,.0f} = ${valor:,.0f} ({calidad}, según {origen}).",
    )


def construir_asiento(factura, propuesta, retencion):
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
        renglon(*CUENTA_IVA_DESCONTABLE, debito=factura.iva)
    if retencion.valor > 0:
        renglon(retencion.cuenta, retencion.nombre_cuenta, credito=retencion.valor)
    contrapartida = (CUENTA_PROVEEDORES if propuesta.cuenta == "1435"
                     else CUENTA_COSTOS_GASTOS_POR_PAGAR)
    renglon(*contrapartida, credito=factura.total - retencion.valor)

    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        # Control del auxiliar: jamás persistir un asiento desbalanceado.
        raise ValueError(f"Asiento desbalanceado: débitos {debitos} ≠ créditos {creditos}.")
    return renglones


def construir_asiento_nota_credito_compra(nota, original):
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
        {"cuenta": CUENTA_COSTOS_GASTOS_POR_PAGAR[0],
         "nombre": CUENTA_COSTOS_GASTOS_POR_PAGAR[1]},
    )
    renglon(por_pagar["cuenta"], por_pagar["nombre"], debito=nota.total)
    renglon(original.cuenta_puc, original.nombre_cuenta_puc, credito=nota.subtotal)
    if nota.iva > 0:
        renglon(*CUENTA_IVA_DESCONTABLE, credito=nota.iva)

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
