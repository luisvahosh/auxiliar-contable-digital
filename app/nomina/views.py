from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .calculo import liquidar_mes
from .forms import FormularioEmpleado, FormularioLiquidar
from .models import Empleado, LiquidacionNomina


def panel(request):
    """Planta de personal + liquidar el mes + historial de liquidaciones."""
    empresa = request.empresa
    return render(request, "nomina/panel.html", {
        "empresa": empresa,
        "empleados": Empleado.objects.de_empresa(empresa),
        "liquidaciones": LiquidacionNomina.objects.de_empresa(empresa),
        "formulario_liquidar": FormularioLiquidar(),
    })


def empleado(request, pk=None):
    """Crear o editar un empleado."""
    empresa = request.empresa
    instancia = (get_object_or_404(Empleado.objects.de_empresa(empresa), pk=pk)
                 if pk else None)
    formulario = FormularioEmpleado(request.POST or None, instance=instancia)
    if request.method == "POST" and formulario.is_valid():
        nuevo = formulario.save(commit=False)
        nuevo.empresa = empresa
        try:
            nuevo.save()
        except IntegrityError:
            formulario.add_error("cedula", "Ya hay un empleado con esa cédula.")
        else:
            messages.success(request, f"Empleado {nuevo.nombre} guardado.")
            return redirect("nomina:panel")
    return render(request, "nomina/empleado_form.html", {
        "formulario": formulario, "instancia": instancia,
    })


@require_POST
def liquidar(request):
    empresa = request.empresa
    formulario = FormularioLiquidar(request.POST)
    if not formulario.is_valid():
        messages.error(request, "Período inválido (formato AAAA-MM).")
        return redirect("nomina:panel")
    anio, mes = formulario.cleaned_data["periodo"]

    # P8.5: un mes se liquida una sola vez
    if LiquidacionNomina.objects.de_empresa(empresa).filter(anio=anio, mes=mes).exists():
        messages.warning(request, f"La nómina {anio}-{mes:02d} ya fue liquidada; "
                                  "no se creó una segunda.")
        return redirect("nomina:panel")

    empleados = list(Empleado.objects.de_empresa(empresa).filter(activo=True))
    if not empleados:
        messages.error(request, "No hay empleados activos: registra la planta primero.")
        return redirect("nomina:panel")

    try:
        resultado = liquidar_mes(empresa, empleados, anio, mes)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("nomina:panel")

    try:
        liquidacion = LiquidacionNomina.objects.create(
            empresa=empresa, anio=anio, mes=mes,
            detalle=resultado["detalle"],
            total_devengado=resultado["totales"]["devengado"],
            total_deducciones=resultado["totales"]["deducciones"],
            total_neto=resultado["totales"]["neto"],
            total_aportes_empleador=resultado["totales"]["aportes_empleador"],
            total_provisiones=resultado["totales"]["provisiones"],
            asiento=resultado["asiento"],
            explicacion=resultado["explicacion"],
        )
    except IntegrityError:
        messages.warning(request, "Esa nómina ya fue liquidada.")
        return redirect("nomina:panel")

    messages.success(request, f"Nómina {anio}-{mes:02d} liquidada, pendiente de tu "
                              "aprobación (P8.6: nada se contabiliza sin tu visto bueno).")
    return redirect("nomina:detalle", pk=liquidacion.pk)


def detalle(request, pk):
    empresa = request.empresa
    liquidacion = get_object_or_404(
        LiquidacionNomina.objects.de_empresa(empresa), pk=pk)
    renglones = [
        {**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
        for r in liquidacion.asiento
    ]
    return render(request, "nomina/detalle.html", {
        "liquidacion": liquidacion,
        "renglones": renglones,
        "total_debitos": sum(r["debito"] for r in renglones),
        "total_creditos": sum(r["credito"] for r in renglones),
    })


@require_POST
def decidir(request, pk, decision):
    empresa = request.empresa
    liquidacion = get_object_or_404(
        LiquidacionNomina.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    if decision not in ("aprobada", "rechazada"):
        return redirect("nomina:detalle", pk=pk)
    liquidacion.estado = decision
    liquidacion.save(update_fields=["estado", "actualizada"])
    if decision == "aprobada":
        messages.success(request, f"Nómina {liquidacion.anio}-{liquidacion.mes:02d} "
                                  "aprobada. PILA y nómina electrónica las presenta "
                                  "el humano (v1 no presenta ante entidades).")
    else:
        messages.info(request, "Liquidación rechazada: corrige la planta o los "
                               "parámetros y vuelve a liquidar (elimínala en el admin).")
    return redirect("nomina:detalle", pk=pk)
