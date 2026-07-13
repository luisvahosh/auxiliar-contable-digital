from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from causacion.models import FacturaCompra, FacturaVenta

from .forms import FormularioSubirExtracto
from .models import ExtractoBancario, MovimientoBancario
from .motor import ExtractoInvalido, parsear_extracto_archivo, sugerir


def _empresa_activa(request):
    """Tenant del request: lo resuelve el middleware desde la sesión (§12)."""
    return request.empresa


def bancos(request):
    """Lista de extractos + carga de uno nuevo."""
    empresa = _empresa_activa(request)
    formulario = FormularioSubirExtracto(request.POST or None, request.FILES or None)

    if request.method == "POST" and formulario.is_valid():
        archivo = formulario.cleaned_data["archivo"]
        try:
            crudos = parsear_extracto_archivo(archivo.name, archivo.read())
        except ExtractoInvalido as error:
            messages.error(request, f"No se pudo procesar el extracto: {error}")
            return render(request, "conciliacion/bancos.html", {
                "formulario": formulario,
                "extractos": ExtractoBancario.objects.de_empresa(empresa),
            })

        # Solo lo aprobado está en libros: contra eso se cruza el extracto.
        ventas = list(FacturaVenta.objects.de_empresa(empresa)
                      .filter(tipo="venta", estado="aprobada"))
        compras = list(FacturaCompra.objects.de_empresa(empresa)
                       .filter(estado="aprobada"))

        extracto = ExtractoBancario.objects.create(
            empresa=empresa, nombre=archivo.name[:120])
        from causacion.plan_cuentas import plan_de_empresa
        cuentas = plan_de_empresa(empresa)
        ventas_usadas, compras_usadas = set(), set()
        for fila, crudo in enumerate(crudos, start=1):
            propuesta = sugerir(crudo, ventas, compras, ventas_usadas,
                                compras_usadas, cuentas)
            MovimientoBancario.objects.create(
                empresa=empresa,
                extracto=extracto,
                fila=fila,
                fecha=crudo["fecha"],
                descripcion=crudo["descripcion"],
                valor=crudo["valor"],
                sugerencia=propuesta["sugerencia"],
                factura_venta=propuesta.get("factura_venta"),
                factura_compra=propuesta.get("factura_compra"),
                asiento=propuesta.get("asiento", []),
                explicacion=propuesta["explicacion"],
            )
        messages.success(
            request,
            f"Extracto {extracto.nombre} procesado: {len(crudos)} movimientos "
            "con su sugerencia de cruce. Revisa y concilia uno a uno.",
        )
        return redirect("conciliacion:extracto", pk=extracto.pk)

    return render(request, "conciliacion/bancos.html", {
        "formulario": formulario,
        "extractos": ExtractoBancario.objects.de_empresa(empresa),
    })


def extracto(request, pk):
    empresa = _empresa_activa(request)
    extracto_obj = get_object_or_404(
        ExtractoBancario.objects.de_empresa(empresa), pk=pk)
    movimientos = list(extracto_obj.movimientos.all())

    # Formato de conciliación (P4.6): lo conciliado explica el extracto;
    # pendientes y excepciones son la diferencia por explicar.
    conciliados = [m for m in movimientos if m.estado == "conciliado"]
    sin_conciliar = [m for m in movimientos if m.estado != "conciliado"]
    resumen = {
        "abonos": sum(m.valor for m in movimientos if m.valor > 0),
        "cargos": sum(m.valor for m in movimientos if m.valor < 0),
        "neto_extracto": sum((m.valor for m in movimientos), Decimal("0")),
        "conciliado": sum((m.valor for m in conciliados), Decimal("0")),
        "diferencia": sum((m.valor for m in sin_conciliar), Decimal("0")),
        "cuantos_pendientes": sum(1 for m in movimientos if m.estado == "pendiente"),
        "cuantas_excepciones": sum(1 for m in movimientos if m.estado == "excepcion"),
        "cuadrada": not sin_conciliar,
    }
    return render(request, "conciliacion/extracto.html", {
        "extracto": extracto_obj,
        "movimientos": movimientos,
        "resumen": resumen,
    })


@require_POST
def conciliar(request, pk):
    empresa = _empresa_activa(request)
    movimiento = get_object_or_404(
        MovimientoBancario.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    if not movimiento.conciliable:
        messages.error(request, "Un movimiento sin identificar no se puede conciliar: "
                                "márcalo como excepción o registra primero la factura.")
        return redirect("conciliacion:extracto", pk=movimiento.extracto_id)
    movimiento.estado = "conciliado"
    movimiento.save(update_fields=["estado"])
    messages.success(request, f"Movimiento «{movimiento.descripcion[:40]}» conciliado.")
    return redirect("conciliacion:extracto", pk=movimiento.extracto_id)


@require_POST
def excepcion(request, pk):
    empresa = _empresa_activa(request)
    movimiento = get_object_or_404(
        MovimientoBancario.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    movimiento.estado = "excepcion"
    movimiento.save(update_fields=["estado"])
    messages.info(request, "Movimiento marcado como excepción: queda documentado "
                           "como partida conciliatoria pendiente.")
    return redirect("conciliacion:extracto", pk=movimiento.extracto_id)
