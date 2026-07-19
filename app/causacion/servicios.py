"""
Motor único de procesamiento de documentos XML (guía P1/P2).

Lo usan todos los canales de ingesta — la subida manual, el lote de carpeta
(comando causar_lote) y, próximo, el buzón de correo (PLAN.md §4) — para que
un canal nuevo jamás duplique validaciones (CUFE, XXE, totales, tenant).
"""
from dataclasses import dataclass

from django.db import IntegrityError

from .clasificacion import (
    calcular_retencion,
    clasificar,
    construir_asiento,
    construir_asiento_nota_credito_compra,
)
from .models import FacturaCompra, FacturaVenta, Tercero
from .parser import (
    FacturaInvalida,
    es_respuesta_dian,
    parsear_factura,
    parsear_respuesta_dian,
)
from .plan_cuentas import plan_de_empresa
from .ventas import construir_asiento_nota_credito, construir_asiento_venta


@dataclass
class Resultado:
    estado: str           # "creado" | "duplicado" | "error"
    mensaje: str          # apto para el usuario o el registro del lote
    documento: object = None
    tipo: str = ""        # "compra" | "venta" | "nc_venta" | "nc_compra"
    reintentable: bool = False  # NC sin original: puede resolverse más tarde en el lote


def tercero_del_emisor(empresa, datos):
    """El proveedor entra a la matriz con su primera factura (guía P3)."""
    tercero, _ = Tercero.objects.de_empresa(empresa).get_or_create(
        nit=datos.nit_emisor,
        defaults={
            "empresa": empresa,
            "razon_social": datos.nombre_emisor,
            "tipo_persona": datos.tipo_persona_emisor,
            "regimen_simple": datos.responsabilidad_emisor == "O-47",
            "autorretenedor": datos.responsabilidad_emisor == "O-15",
        },
    )
    return tercero


def procesar_xml(empresa, contenido):
    """Un XML (bytes) → documento causado/registrado, duplicado o error.

    Un mismo 'subir XML' acepta también el ApplicationResponse de la DIAN
    (resultado de validación de una factura emitida, P6.3)."""
    if es_respuesta_dian(contenido):
        return _aplicar_respuesta_dian(empresa, contenido)
    try:
        datos = parsear_factura(contenido)
    except FacturaInvalida as error:
        return Resultado("error", f"No se pudo procesar el XML: {error}")

    es_emisor = datos.nit_emisor == empresa.nit
    es_adquiriente = datos.nit_adquiriente == empresa.nit

    if datos.tipo_documento == "nota_credito":
        if es_emisor:
            return _nota_credito_venta(empresa, datos, contenido)
        if es_adquiriente:
            return _nota_credito_compra(empresa, datos, contenido)
    elif es_adquiriente:
        return _compra(empresa, datos, contenido)
    elif es_emisor:
        return _venta(empresa, datos, contenido)
    return Resultado(
        "error",
        f"El documento no menciona a {empresa.razon_social} (NIT {empresa.nit}): "
        f"emisor {datos.nit_emisor}, adquiriente {datos.nit_adquiriente}.",
    )


def _aplicar_respuesta_dian(empresa, contenido):
    """Refleja en la factura emitida el resultado de validación de la DIAN (P6.3)."""
    try:
        rta = parsear_respuesta_dian(contenido)
    except FacturaInvalida as error:
        return Resultado("error", f"No se pudo leer la respuesta DIAN: {error}")

    ventas = FacturaVenta.objects.de_empresa(empresa)
    factura = None
    if rta.cufe_referencia:
        factura = ventas.filter(cufe=rta.cufe_referencia).first()
    if factura is None and rta.numero_referencia:
        factura = ventas.filter(numero=rta.numero_referencia).first()
    if factura is None:
        ref = rta.numero_referencia or rta.cufe_referencia or "sin identificar"
        return Resultado(
            "error",
            f"La respuesta de la DIAN es sobre la factura {ref}, que no está "
            "registrada en esta empresa. Registra primero la factura emitida.",
        )

    if rta.estado == "indeterminado":
        # No se pudo clasificar el código: se guarda el motivo, queda pendiente
        # para revisión humana (no se marca aceptada/rechazada a la ligera).
        factura.motivo_dian = (
            f"[código DIAN {rta.codigo}] {rta.motivo}").strip()
        factura.fecha_estado_dian = rta.fecha
        factura.save(update_fields=["motivo_dian", "fecha_estado_dian", "actualizada"])
        return Resultado(
            "creado",
            f"Respuesta de la DIAN registrada sobre {factura.numero}, pero el "
            f"código «{rta.codigo}» no es concluyente; revísala manualmente.",
            documento=factura, tipo="respuesta_dian",
        )

    factura.estado_dian = rta.estado
    factura.motivo_dian = rta.motivo
    factura.fecha_estado_dian = rta.fecha
    if rta.estado == "aceptada":
        factura.rechazo_notificado = None  # por si venía de un rechazo corregido
    factura.save(update_fields=["estado_dian", "motivo_dian", "fecha_estado_dian",
                                "rechazo_notificado", "actualizada"])
    verbo = "RECHAZADA" if rta.estado == "rechazada" else "aceptada"
    return Resultado(
        "creado",
        f"La DIAN marcó la factura {factura.numero} como {verbo}."
        + (f" Motivo: {rta.motivo}" if rta.estado == "rechazada" and rta.motivo else ""),
        documento=factura, tipo="respuesta_dian",
    )


def _compra(empresa, datos, contenido):
    existente = FacturaCompra.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        return Resultado("duplicado",
                         f"La factura {existente.numero} ya fue causada (CUFE duplicado). "
                         "No se creó un asiento doble.", existente, "compra")

    plan = plan_de_empresa(empresa)
    tercero = tercero_del_emisor(empresa, datos)
    propuesta = clasificar(datos, plan, tercero)
    retencion = calcular_retencion(datos, propuesta.concepto, tercero, plan)
    renglones = construir_asiento(datos, propuesta, retencion, plan)
    try:
        factura = FacturaCompra.objects.create(
            empresa=empresa,
            cufe=datos.cufe,
            numero=datos.numero,
            fecha_emision=datos.fecha_emision,
            nit_emisor=datos.nit_emisor,
            nombre_emisor=datos.nombre_emisor,
            tipo_persona_emisor=datos.tipo_persona_emisor,
            responsabilidad_emisor=datos.responsabilidad_emisor,
            subtotal=datos.subtotal,
            iva=datos.iva,
            total=datos.total,
            retencion=retencion.valor,
            cuenta_puc=propuesta.cuenta,
            nombre_cuenta_puc=propuesta.nombre_cuenta,
            concepto_retencion=propuesta.concepto,
            nivel=propuesta.nivel,
            explicacion=f"{propuesta.explicacion}\n{retencion.porque}",
            asiento=renglones,
            xml_crudo=contenido.decode("utf-8", errors="replace"),
        )
    except IntegrityError:
        # Carrera entre dos ingestas simultáneas: la restricción única manda.
        return Resultado("duplicado", "Esa factura ya fue causada (CUFE duplicado).")
    return Resultado("creado",
                     f"Compra {factura.numero} procesada — propuesta "
                     f"{factura.get_nivel_display().lower()}, pendiente de tu aprobación.",
                     factura, "compra")


def _venta(empresa, datos, contenido):
    existente = FacturaVenta.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        return Resultado("duplicado",
                         f"La venta {existente.numero} ya fue registrada (CUFE duplicado). "
                         "No se creó un asiento doble.", existente, "venta")

    renglones, explicacion = construir_asiento_venta(datos, plan_de_empresa(empresa))
    try:
        venta = FacturaVenta.objects.create(
            empresa=empresa,
            tipo="venta",
            cufe=datos.cufe,
            numero=datos.numero,
            fecha_emision=datos.fecha_emision,
            fecha_vencimiento=datos.fecha_vencimiento,
            nit_cliente=datos.nit_adquiriente,
            nombre_cliente=datos.nombre_adquiriente,
            correo_cliente=datos.correo_adquiriente,
            subtotal=datos.subtotal,
            iva=datos.iva,
            total=datos.total,
            retencion_practicada=datos.retefuente_practicada,
            explicacion=explicacion,
            asiento=renglones,
            xml_crudo=contenido.decode("utf-8", errors="replace"),
        )
    except IntegrityError:
        return Resultado("duplicado", "Esa venta ya fue registrada (CUFE duplicado).")
    return Resultado("creado",
                     f"Venta {venta.numero} registrada, pendiente de tu aprobación.",
                     venta, "venta")


def _nota_credito_venta(empresa, datos, contenido):
    existente = FacturaVenta.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        return Resultado("duplicado",
                         f"La nota crédito {existente.numero} ya fue registrada.",
                         existente, "nc_venta")

    ventas = FacturaVenta.objects.de_empresa(empresa).filter(tipo="venta")
    original = None
    if datos.referencia_cufe:
        original = ventas.filter(cufe=datos.referencia_cufe).first()
    if original is None and datos.referencia_numero:
        original = ventas.filter(numero=datos.referencia_numero).first()
    if original is None:
        return Resultado(
            "error",
            f"La nota crédito {datos.numero} referencia la factura "
            f"{datos.referencia_numero or datos.referencia_cufe[:12]}, que no está "
            "registrada. Sube primero la factura de venta original.",
            reintentable=True)

    renglones, explicacion = construir_asiento_nota_credito(
        datos, original, plan_de_empresa(empresa))
    nota = FacturaVenta.objects.create(
        empresa=empresa,
        tipo="nota_credito",
        factura_original=original,
        cufe=datos.cufe,
        numero=datos.numero,
        fecha_emision=datos.fecha_emision,
        nit_cliente=datos.nit_adquiriente,
        nombre_cliente=datos.nombre_adquiriente,
        subtotal=datos.subtotal,
        iva=datos.iva,
        total=datos.total,
        explicacion=explicacion,
        asiento=renglones,
        xml_crudo=contenido.decode("utf-8", errors="replace"),
    )
    return Resultado("creado",
                     f"Nota crédito {nota.numero} registrada, vinculada a "
                     f"{original.numero}, pendiente de tu aprobación.",
                     nota, "nc_venta")


def _nota_credito_compra(empresa, datos, contenido):
    existente = FacturaCompra.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        return Resultado("duplicado",
                         f"La nota crédito {existente.numero} ya fue registrada.",
                         existente, "nc_compra")

    compras = FacturaCompra.objects.de_empresa(empresa).filter(tipo="compra")
    original = None
    if datos.referencia_cufe:
        original = compras.filter(cufe=datos.referencia_cufe).first()
    if original is None and datos.referencia_numero:
        original = compras.filter(numero=datos.referencia_numero).first()
    if original is None:
        return Resultado(
            "error",
            f"La nota crédito {datos.numero} referencia la compra "
            f"{datos.referencia_numero or datos.referencia_cufe[:12]}, que no está "
            "causada. Causa primero la factura original del proveedor.",
            reintentable=True)

    renglones, explicacion = construir_asiento_nota_credito_compra(
        datos, original, plan_de_empresa(empresa))
    nota = FacturaCompra.objects.create(
        empresa=empresa,
        tipo="nota_credito",
        factura_original=original,
        cufe=datos.cufe,
        numero=datos.numero,
        fecha_emision=datos.fecha_emision,
        nit_emisor=datos.nit_emisor,
        nombre_emisor=datos.nombre_emisor,
        tipo_persona_emisor=datos.tipo_persona_emisor,
        responsabilidad_emisor=datos.responsabilidad_emisor,
        subtotal=datos.subtotal,
        iva=datos.iva,
        total=datos.total,
        retencion=0,
        cuenta_puc=original.cuenta_puc,
        nombre_cuenta_puc=original.nombre_cuenta_puc,
        nivel="automatica",
        explicacion=explicacion,
        asiento=renglones,
        xml_crudo=contenido.decode("utf-8", errors="replace"),
    )
    return Resultado("creado",
                     f"Nota crédito de proveedor {nota.numero} registrada, vinculada a "
                     f"{original.numero}, pendiente de tu aprobación.",
                     nota, "nc_compra")
