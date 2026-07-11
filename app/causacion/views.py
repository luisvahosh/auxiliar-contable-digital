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
from .forms import FormularioSubirFactura
from .models import FacturaCompra, MapeoCuentaAlegra
from .parser import FacturaInvalida, parsear_factura
from .siigo import generar_csv_siigo


def _empresa_activa(request):
    """Tenant del request. Beta cero: la única empresa registrada.
    Cuando lleguen usuarios (core), saldrá de la sesión/membresía."""
    return Empresa.objects.order_by("creada").first()


def bandeja(request):
    empresa = _empresa_activa(request)
    facturas = FacturaCompra.objects.de_empresa(empresa)
    return render(request, "causacion/bandeja.html", {
        "empresa": empresa,
        "facturas": facturas,
        "pendientes": facturas.filter(estado="pendiente").count(),
    })


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

        if datos.nit_adquiriente != empresa.nit:
            messages.error(
                request,
                f"La factura está dirigida al NIT {datos.nit_adquiriente}, "
                f"que no es el de {empresa.razon_social} (NIT {empresa.nit}).",
            )
            return render(request, "causacion/subir.html", {"formulario": formulario})

        # Control P1.5: la misma factura (CUFE) no se causa dos veces.
        existente = FacturaCompra.objects.de_empresa(empresa).filter(cufe=datos.cufe).first()
        if existente:
            messages.warning(
                request,
                f"La factura {existente.numero} ya fue causada (CUFE duplicado). "
                "No se creó un asiento doble.",
            )
            return redirect("causacion:detalle", pk=existente.pk)

        propuesta = clasificar(datos)
        retencion = calcular_retencion(datos, propuesta.concepto)
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
            f"Factura {factura.numero} procesada — propuesta "
            f"{factura.get_nivel_display().lower()}, pendiente de tu aprobación.",
        )
        return redirect("causacion:detalle", pk=factura.pk)

    return render(request, "causacion/subir.html", {"formulario": formulario})


def detalle(request, pk):
    empresa = _empresa_activa(request)
    factura = get_object_or_404(FacturaCompra.objects.de_empresa(empresa), pk=pk)
    renglones = [
        {**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
        for r in factura.asiento
    ]
    return render(request, "causacion/detalle.html", {
        "factura": factura,
        "renglones": renglones,
        "total_debitos": sum(r["debito"] for r in renglones),
        "total_creditos": sum(r["credito"] for r in renglones),
        "alegra_configurado": alegra.esta_configurado(),
    })


@require_POST
def aprobar(request, pk):
    empresa = _empresa_activa(request)
    factura = get_object_or_404(
        FacturaCompra.objects.de_empresa(empresa), pk=pk, estado="pendiente"
    )
    factura.estado = "aprobada"
    factura.save(update_fields=["estado", "actualizada"])
    messages.success(
        request,
        f"Asiento de la factura {factura.numero} aprobado. "
        "El envío a Alegra y el export CSV Siigo llegan en el siguiente paso del vertical.",
    )
    return redirect("causacion:detalle", pk=factura.pk)


def exportar_siigo(request, pk):
    """Descarga el asiento aprobado como CSV importable en Siigo (P1.9)."""
    empresa = _empresa_activa(request)
    factura = get_object_or_404(
        FacturaCompra.objects.de_empresa(empresa), pk=pk, estado="aprobada"
    )
    contenido = generar_csv_siigo(factura)
    respuesta = HttpResponse(
        contenido.encode("utf-8-sig"),  # BOM: Excel abre bien las tildes
        content_type="text/csv; charset=utf-8",
    )
    respuesta["Content-Disposition"] = f'attachment; filename="siigo-{factura.numero}.csv"'
    return respuesta


@require_POST
def enviar_alegra(request, pk):
    """Crea el asiento aprobado en Alegra vía API (P1.9)."""
    empresa = _empresa_activa(request)
    factura = get_object_or_404(
        FacturaCompra.objects.de_empresa(empresa), pk=pk, estado="aprobada"
    )
    if factura.id_alegra:
        messages.info(request, f"Esta factura ya está en Alegra (asiento #{factura.id_alegra}).")
        return redirect("causacion:detalle", pk=factura.pk)

    mapeo = dict(
        MapeoCuentaAlegra.objects.de_empresa(empresa)
        .values_list("cuenta_puc", "id_alegra")
    )
    try:
        id_alegra = alegra.enviar_asiento(factura, mapeo)
    except alegra.AlegraNoConfigurado as aviso:
        messages.warning(request, str(aviso))
        return redirect("causacion:detalle", pk=factura.pk)
    except alegra.ErrorAlegra as error:
        messages.error(request, str(error))
        return redirect("causacion:detalle", pk=factura.pk)

    factura.id_alegra = id_alegra
    factura.enviada_alegra = timezone.now()
    factura.save(update_fields=["id_alegra", "enviada_alegra", "actualizada"])
    messages.success(request, f"Asiento creado en Alegra con id #{id_alegra}.")
    return redirect("causacion:detalle", pk=factura.pk)


@require_POST
def rechazar(request, pk):
    empresa = _empresa_activa(request)
    factura = get_object_or_404(
        FacturaCompra.objects.de_empresa(empresa), pk=pk, estado="pendiente"
    )
    factura.estado = "rechazada"
    factura.save(update_fields=["estado", "actualizada"])
    messages.info(
        request,
        f"Propuesta de la factura {factura.numero} rechazada: no se contabilizará. "
        "La reclasificación manual llega con la matriz de terceros.",
    )
    return redirect("causacion:detalle", pk=factura.pk)
