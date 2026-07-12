from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Empresa

from . import alegra
from .clasificacion import calcular_retencion, clasificar, construir_asiento
from .forms import FormularioSubirFactura, FormularioTercero
from .models import FacturaCompra, FacturaVenta, MapeoCuentaAlegra, Tercero
from .parser import FacturaInvalida, parsear_factura
from .siigo import generar_csv_siigo
from .ventas import (
    consecutivos_faltantes,
    construir_asiento_nota_credito,
    construir_asiento_venta,
)


def _empresa_activa(request):
    """Tenant del request. Beta cero: la única empresa registrada.
    Cuando lleguen usuarios (core), saldrá de la sesión/membresía."""
    return Empresa.objects.order_by("creada").first()


# ---------- Subida única: la app decide si es compra, venta o nota crédito ----------

def subir(request):
    empresa = _empresa_activa(request)
    formulario = FormularioSubirFactura(request.POST or None, request.FILES or None)

    if request.method == "POST" and formulario.is_valid():
        contenido = formulario.cleaned_data["archivo"].read()
        try:
            datos = parsear_factura(contenido)
        except FacturaInvalida as error:
            messages.error(request, f"No se pudo procesar el XML: {error}")
            return render(request, "causacion/subir.html", {"formulario": formulario})

        es_emisor = datos.nit_emisor == empresa.nit
        es_adquiriente = datos.nit_adquiriente == empresa.nit

        if datos.tipo_documento == "nota_credito":
            if es_emisor:
                return _registrar_nota_credito(request, empresa, datos, contenido)
            messages.error(
                request,
                "Las notas crédito de proveedores (compras) aún no están soportadas; "
                "por ahora solo las emitidas por tu empresa.",
            )
        elif es_adquiriente:
            return _causar_compra(request, empresa, datos, contenido)
        elif es_emisor:
            return _registrar_venta(request, empresa, datos, contenido)
        else:
            messages.error(
                request,
                f"El documento no menciona a {empresa.razon_social} (NIT {empresa.nit}): "
                f"emisor {datos.nit_emisor}, adquiriente {datos.nit_adquiriente}.",
            )
        return render(request, "causacion/subir.html", {"formulario": formulario})

    return render(request, "causacion/subir.html", {"formulario": formulario})


def _causar_compra(request, empresa, datos, contenido):
    # Control P1.5: la misma factura (CUFE) no se causa dos veces.
    existente = FacturaCompra.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        messages.warning(
            request,
            f"La factura {existente.numero} ya fue causada (CUFE duplicado). "
            "No se creó un asiento doble.",
        )
        return redirect("causacion:detalle", pk=existente.pk)

    # Matriz de terceros (P3): el proveedor se registra con su primera factura
    # (calidad tomada del XML, pendiente de verificar contra el RUT) y en
    # adelante su calidad registrada manda sobre lo que diga el XML.
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

    propuesta = clasificar(datos)
    retencion = calcular_retencion(datos, propuesta.concepto, tercero)
    renglones = construir_asiento(datos, propuesta, retencion)
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
        # Carrera entre dos subidas simultáneas: la restricción única manda.
        messages.warning(request, "Esa factura ya fue causada (CUFE duplicado).")
        return redirect("causacion:bandeja")

    messages.success(
        request,
        f"Compra {factura.numero} procesada — propuesta "
        f"{factura.get_nivel_display().lower()}, pendiente de tu aprobación.",
    )
    return redirect("causacion:detalle", pk=factura.pk)


def _registrar_venta(request, empresa, datos, contenido):
    existente = FacturaVenta.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        messages.warning(request, f"La venta {existente.numero} ya fue registrada "
                                  "(CUFE duplicado). No se creó un asiento doble.")
        return redirect("causacion:detalle_venta", pk=existente.pk)

    renglones, explicacion = construir_asiento_venta(datos)
    try:
        venta = FacturaVenta.objects.create(
            empresa=empresa,
            tipo="venta",
            cufe=datos.cufe,
            numero=datos.numero,
            fecha_emision=datos.fecha_emision,
            nit_cliente=datos.nit_adquiriente,
            nombre_cliente=datos.nombre_adquiriente,
            subtotal=datos.subtotal,
            iva=datos.iva,
            total=datos.total,
            retencion_practicada=datos.retefuente_practicada,
            explicacion=explicacion,
            asiento=renglones,
            xml_crudo=contenido.decode("utf-8", errors="replace"),
        )
    except IntegrityError:
        messages.warning(request, "Esa venta ya fue registrada (CUFE duplicado).")
        return redirect("causacion:bandeja_ventas")

    messages.success(request, f"Venta {venta.numero} registrada, pendiente de tu aprobación.")
    _alertar_consecutivo(request, empresa)
    return redirect("causacion:detalle_venta", pk=venta.pk)


def _registrar_nota_credito(request, empresa, datos, contenido):
    existente = FacturaVenta.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
    if existente:
        messages.warning(request, f"La nota crédito {existente.numero} ya fue registrada.")
        return redirect("causacion:detalle_venta", pk=existente.pk)

    ventas = FacturaVenta.objects.de_empresa(empresa).filter(tipo="venta")
    original = None
    if datos.referencia_cufe:
        original = ventas.filter(cufe=datos.referencia_cufe).first()
    if original is None and datos.referencia_numero:
        original = ventas.filter(numero=datos.referencia_numero).first()
    if original is None:
        messages.error(
            request,
            f"La nota crédito {datos.numero} referencia la factura "
            f"{datos.referencia_numero or datos.referencia_cufe[:12]}, que no está "
            "registrada. Sube primero la factura de venta original.",
        )
        return redirect("causacion:subir")

    renglones, explicacion = construir_asiento_nota_credito(datos, original)
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
    messages.success(request, f"Nota crédito {nota.numero} registrada, vinculada a "
                              f"{original.numero}, pendiente de tu aprobación.")
    return redirect("causacion:detalle_venta", pk=nota.pk)


def _alertar_consecutivo(request, empresa):
    """Control P2.3: avisar si falta alguna factura en la numeración."""
    numeros = FacturaVenta.objects.de_empresa(empresa).filter(
        tipo="venta").values_list("numero", flat=True)
    faltantes = consecutivos_faltantes(numeros)
    if faltantes:
        messages.warning(
            request,
            "Hueco en el consecutivo de facturación: falta " + ", ".join(faltantes) +
            ". Verifica en la DIAN si fueron anuladas o no se han descargado.",
        )


# ---------- Bandejas y detalles ----------

def bandeja(request):
    empresa = _empresa_activa(request)
    facturas = FacturaCompra.objects.de_empresa(empresa)
    return render(request, "causacion/bandeja.html", {
        "empresa": empresa,
        "facturas": facturas,
        "pendientes": facturas.filter(estado="pendiente").count(),
    })


def bandeja_ventas(request):
    empresa = _empresa_activa(request)
    ventas = FacturaVenta.objects.de_empresa(empresa)
    faltantes = consecutivos_faltantes(
        ventas.filter(tipo="venta").values_list("numero", flat=True))
    return render(request, "causacion/bandeja_ventas.html", {
        "empresa": empresa,
        "ventas": ventas,
        "pendientes": ventas.filter(estado="pendiente").count(),
        "faltantes": faltantes,
    })


def _renglones_decimales(asiento):
    renglones = [
        {**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
        for r in asiento
    ]
    return {
        "renglones": renglones,
        "total_debitos": sum(r["debito"] for r in renglones),
        "total_creditos": sum(r["credito"] for r in renglones),
    }


def detalle(request, pk):
    empresa = _empresa_activa(request)
    factura = get_object_or_404(FacturaCompra.objects.de_empresa(empresa), pk=pk)
    return render(request, "causacion/detalle.html", {
        "factura": factura,
        "alegra_configurado": alegra.esta_configurado(),
        **_renglones_decimales(factura.asiento),
    })


def detalle_venta(request, pk):
    empresa = _empresa_activa(request)
    venta = get_object_or_404(FacturaVenta.objects.de_empresa(empresa), pk=pk)
    return render(request, "causacion/detalle_venta.html", {
        "venta": venta,
        "alegra_configurado": alegra.esta_configurado(),
        **_renglones_decimales(venta.asiento),
    })


# ---------- Matriz de terceros (P3) ----------

def terceros(request):
    empresa = _empresa_activa(request)
    lista = Tercero.objects.de_empresa(empresa)
    return render(request, "causacion/terceros.html", {
        "terceros": lista,
        "sin_verificar": lista.filter(verificado=False).count(),
    })


def editar_tercero(request, pk):
    empresa = _empresa_activa(request)
    tercero = get_object_or_404(Tercero.objects.de_empresa(empresa), pk=pk)
    formulario = FormularioTercero(request.POST or None, instance=tercero)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            f"Tercero {tercero.razon_social} actualizado. Las próximas facturas "
            "de este proveedor usarán esta calidad tributaria.",
        )
        return redirect("causacion:terceros")
    return render(request, "causacion/tercero_form.html", {
        "formulario": formulario,
        "tercero": tercero,
    })


# ---------- Decisión humana y salida al software contable (compras y ventas) ----------

def _decidir(request, modelo, pk, estado, nombre_detalle, mensaje):
    empresa = _empresa_activa(request)
    documento = get_object_or_404(
        modelo.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    documento.estado = estado
    documento.save(update_fields=["estado", "actualizada"])
    (messages.success if estado == "aprobada" else messages.info)(
        request, mensaje.format(numero=documento.numero))
    return redirect(nombre_detalle, pk=documento.pk)


@require_POST
def aprobar(request, pk):
    return _decidir(request, FacturaCompra, pk, "aprobada", "causacion:detalle",
                    "Asiento de la factura {numero} aprobado.")


@require_POST
def rechazar(request, pk):
    return _decidir(request, FacturaCompra, pk, "rechazada", "causacion:detalle",
                    "Propuesta de la factura {numero} rechazada: no se contabilizará.")


@require_POST
def aprobar_venta(request, pk):
    return _decidir(request, FacturaVenta, pk, "aprobada", "causacion:detalle_venta",
                    "Asiento de {numero} aprobado.")


@require_POST
def rechazar_venta(request, pk):
    return _decidir(request, FacturaVenta, pk, "rechazada", "causacion:detalle_venta",
                    "Registro de {numero} rechazado: no se contabilizará.")


def _exportar_siigo(request, modelo, pk):
    """Descarga el asiento aprobado como CSV importable en Siigo (P1.9)."""
    empresa = _empresa_activa(request)
    documento = get_object_or_404(
        modelo.objects.de_empresa(empresa), pk=pk, estado="aprobada")
    respuesta = HttpResponse(
        generar_csv_siigo(documento).encode("utf-8-sig"),  # BOM: Excel abre bien las tildes
        content_type="text/csv; charset=utf-8",
    )
    respuesta["Content-Disposition"] = f'attachment; filename="siigo-{documento.numero}.csv"'
    return respuesta


def exportar_siigo(request, pk):
    return _exportar_siigo(request, FacturaCompra, pk)


def exportar_siigo_venta(request, pk):
    return _exportar_siigo(request, FacturaVenta, pk)


def _enviar_alegra(request, modelo, pk, nombre_detalle):
    """Crea el asiento aprobado en Alegra vía API (P1.9)."""
    empresa = _empresa_activa(request)
    documento = get_object_or_404(
        modelo.objects.de_empresa(empresa), pk=pk, estado="aprobada")
    if documento.id_alegra:
        messages.info(request, f"{documento.numero} ya está en Alegra "
                               f"(asiento #{documento.id_alegra}).")
        return redirect(nombre_detalle, pk=documento.pk)

    mapeo = dict(
        MapeoCuentaAlegra.objects.de_empresa(empresa)
        .values_list("cuenta_puc", "id_alegra")
    )
    try:
        id_alegra = alegra.enviar_asiento(documento, mapeo)
    except alegra.AlegraNoConfigurado as aviso:
        messages.warning(request, str(aviso))
        return redirect(nombre_detalle, pk=documento.pk)
    except alegra.ErrorAlegra as error:
        messages.error(request, str(error))
        return redirect(nombre_detalle, pk=documento.pk)

    documento.id_alegra = id_alegra
    documento.enviada_alegra = timezone.now()
    documento.save(update_fields=["id_alegra", "enviada_alegra", "actualizada"])
    messages.success(request, f"Asiento creado en Alegra con id #{id_alegra}.")
    return redirect(nombre_detalle, pk=documento.pk)


@require_POST
def enviar_alegra(request, pk):
    return _enviar_alegra(request, FacturaCompra, pk, "causacion:detalle")


@require_POST
def enviar_alegra_venta(request, pk):
    return _enviar_alegra(request, FacturaVenta, pk, "causacion:detalle_venta")
