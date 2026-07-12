import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import alegra, vision
from .cartera import RANGOS, edades_de_cartera
from .clasificacion import calcular_retencion, clasificar, construir_asiento
from .forms import (
    TIPOS_IMAGEN,
    FormularioFacturaFisica,
    FormularioFotoFactura,
    FormularioSubirFactura,
    FormularioTercero,
)
from .models import FacturaCompra, FacturaVenta, MapeoCuentaAlegra, Tercero
from .parser import FacturaParseada, Linea
from .servicios import procesar_xml, tercero_del_emisor
from .siigo import generar_csv_siigo
from .ventas import consecutivos_faltantes

CARPETA_FOTOS = "facturas_fisicas"
# Solo nombres que nosotros mismos generamos (anti path-traversal)
PATRON_NOMBRE_FOTO = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")


def _empresa_activa(request):
    """Tenant del request: lo resuelve el middleware desde la sesión (§12)."""
    return request.empresa


# ---------- Subida única: la app decide si es compra, venta o nota crédito ----------

def subir(request):
    empresa = _empresa_activa(request)
    formulario = FormularioSubirFactura(request.POST or None, request.FILES or None)

    if request.method == "POST" and formulario.is_valid():
        resultado = procesar_xml(empresa, formulario.cleaned_data["archivo"].read())
        if resultado.estado == "error":
            messages.error(request, resultado.mensaje)
            return render(request, "causacion/subir.html", {"formulario": formulario})
        if resultado.estado == "duplicado":
            messages.warning(request, resultado.mensaje)
        else:
            messages.success(request, resultado.mensaje)
            if resultado.tipo == "venta":
                _alertar_consecutivo(request, empresa)
        destino = ("causacion:detalle" if resultado.tipo in ("compra", "nc_compra")
                   else "causacion:detalle_venta")
        return redirect(destino, pk=resultado.documento.pk)

    return render(request, "causacion/subir.html", {"formulario": formulario})


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


# ---------- Factura física fotografiada (P1.10) ----------

def foto(request):
    """Paso 1: subir/tomar la foto; si la IA de visión está configurada,
    extrae los campos y prellena el formulario de confirmación."""
    formulario = FormularioFotoFactura(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        archivo = formulario.cleaned_data["foto"]
        contenido = archivo.read()
        nombre = f"{uuid4().hex}{TIPOS_IMAGEN[archivo.content_type]}"
        carpeta = Path(settings.MEDIA_ROOT) / CARPETA_FOTOS
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_bytes(contenido)

        iniciales, confianza = {}, None
        if vision.esta_configurada():
            try:
                campos = vision.extraer_campos(contenido, archivo.content_type)
                confianza = campos.pop("confianza", None)
                iniciales = {clave: valor for clave, valor in campos.items()
                             if valor not in (None, "")}
                if "nit_emisor" in iniciales:
                    iniciales["nit_emisor"] = re.sub(r"\D", "", str(iniciales["nit_emisor"]))
                messages.info(request,
                              "Campos extraídos por la IA de visión: revísalos UNO POR UNO "
                              "contra la factura antes de causar.")
            except vision.ErrorVision as error:
                messages.warning(request,
                                 f"No se pudieron extraer los campos ({error}) — "
                                 "digítalos manualmente; la foto queda como soporte.")
        else:
            messages.info(request,
                          "La IA de visión no está configurada (NVIDIA_API_KEY en .env): "
                          "digita los campos manualmente; la foto queda como soporte.")
        return render(request, "causacion/foto_confirmar.html", {
            "formulario": FormularioFacturaFisica(initial=iniciales),
            "nombre_foto": nombre,
            "confianza": confianza,
        })
    return render(request, "causacion/foto.html", {"formulario": formulario})


@require_POST
def foto_causar(request):
    """Paso 2: el usuario confirmó los campos → causar como SUGERIDA (P1.10)."""
    empresa = _empresa_activa(request)
    nombre_foto = request.POST.get("nombre_foto", "")
    if not PATRON_NOMBRE_FOTO.fullmatch(nombre_foto):
        messages.error(request, "Referencia de foto inválida; vuelve a subirla.")
        return redirect("causacion:foto")

    formulario = FormularioFacturaFisica(request.POST)
    if not formulario.is_valid():
        return render(request, "causacion/foto_confirmar.html", {
            "formulario": formulario, "nombre_foto": nombre_foto, "confianza": None,
        })
    campos = formulario.cleaned_data

    # Sin CUFE (papel): antiduplicado por NIT + número + fecha.
    pseudo_cufe = f"FISICA:{campos['nit_emisor']}:{campos['numero']}:{campos['fecha'].isoformat()}"
    existente = FacturaCompra.objects.de_empresa(empresa).filter(cufe=pseudo_cufe).first()
    if existente:
        messages.warning(request, f"La factura {existente.numero} de ese proveedor y fecha "
                                  "ya fue causada. No se creó un asiento doble.")
        return redirect("causacion:detalle", pk=existente.pk)

    datos = FacturaParseada(
        cufe=pseudo_cufe,
        numero=campos["numero"],
        fecha_emision=campos["fecha"],
        nota=campos["concepto"],
        nit_emisor=campos["nit_emisor"],
        nombre_emisor=campos["nombre_emisor"],
        tipo_persona_emisor=campos["tipo_persona"],
        responsabilidad_emisor="",
        nit_adquiriente=empresa.nit,
        nombre_adquiriente=empresa.razon_social,
        subtotal=campos["subtotal"],
        iva=campos["iva"],
        total=campos["total"],
        lineas=[Linea(descripcion=campos["concepto"], cantidad=Decimal("1"),
                      valor=campos["subtotal"])],
        tipo_documento="factura",
        retefuente_practicada=Decimal("0"),
        referencia_numero="",
        referencia_cufe="",
    )
    tercero = tercero_del_emisor(empresa, datos)
    propuesta = clasificar(datos)
    retencion = calcular_retencion(datos, propuesta.concepto, tercero)
    renglones = construir_asiento(datos, propuesta, retencion)
    try:
        factura = FacturaCompra.objects.create(
            empresa=empresa,
            cufe=pseudo_cufe,
            numero=datos.numero,
            fecha_emision=datos.fecha_emision,
            nit_emisor=datos.nit_emisor,
            nombre_emisor=datos.nombre_emisor,
            tipo_persona_emisor=datos.tipo_persona_emisor,
            responsabilidad_emisor="",
            subtotal=datos.subtotal,
            iva=datos.iva,
            total=datos.total,
            retencion=retencion.valor,
            cuenta_puc=propuesta.cuenta,
            nombre_cuenta_puc=propuesta.nombre_cuenta,
            concepto_retencion=propuesta.concepto,
            nivel="sugerida",  # P1.10: lo que viene de foto NUNCA es automático
            explicacion=("Causada desde foto de factura física: campos confirmados "
                         "por el usuario; entra siempre como sugerida (P1.10).\n"
                         f"{propuesta.explicacion}\n{retencion.porque}"),
            asiento=renglones,
            xml_crudo="(factura física — el soporte es la fotografía adjunta)",
            origen="foto",
            imagen=f"{CARPETA_FOTOS}/{nombre_foto}",
        )
    except IntegrityError:
        messages.warning(request, "Esa factura ya fue causada.")
        return redirect("causacion:bandeja")

    messages.success(request, f"Factura física {factura.numero} causada como sugerida, "
                              "pendiente de tu aprobación.")
    return redirect("causacion:detalle", pk=factura.pk)


# ---------- Cartera (P5.1) ----------

def cartera(request):
    empresa = _empresa_activa(request)
    partidas, totales = edades_de_cartera(empresa)
    return render(request, "causacion/cartera.html", {
        "empresa": empresa,
        "partidas": partidas,
        "rangos": [(clave, etiqueta, totales[clave]) for clave, etiqueta in RANGOS],
        "total_cartera": sum(totales.values()),
        "hay_asumidos": any(partida["vencimiento_asumido"] for partida in partidas),
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
