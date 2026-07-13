from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from collections import defaultdict

from .calculo import liquidar_mes
from .forms import (
    FormularioEmpleado,
    FormularioImportarEmpleados,
    FormularioLiquidar,
    FormularioNovedad,
)
from .importar import ImportacionInvalida, leer_empleados
from .models import Empleado, LiquidacionNomina, NovedadNomina


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


def novedades(request):
    """Registrar y listar las novedades del mes (P8.8)."""
    empresa = request.empresa
    formulario = FormularioNovedad(request.POST or None, empresa=empresa)
    if request.method == "POST" and formulario.is_valid():
        novedad = formulario.save(commit=False)
        novedad.empresa = empresa
        novedad.anio, novedad.mes = formulario.cleaned_data["periodo"]
        novedad.save()
        messages.success(request, f"Novedad registrada para {novedad.empleado.nombre}. "
                                  "Se aplicará al liquidar ese mes.")
        return redirect("nomina:novedades")
    return render(request, "nomina/novedades.html", {
        "formulario": formulario,
        "novedades": NovedadNomina.objects.de_empresa(empresa)
                     .select_related("empleado")[:60],
    })


@require_POST
def borrar_novedad(request, pk):
    empresa = request.empresa
    novedad = get_object_or_404(NovedadNomina.objects.de_empresa(empresa), pk=pk)
    novedad.delete()
    messages.info(request, "Novedad eliminada.")
    return redirect("nomina:novedades")


def importar_empleados(request):
    """Carga masiva de la planta desde CSV. Reentrante: la cédula ya
    registrada se actualiza, no se duplica."""
    empresa = request.empresa
    formulario = FormularioImportarEmpleados(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            validos, errores = leer_empleados(formulario.cleaned_data["archivo"].read())
        except ImportacionInvalida as error:
            messages.error(request, f"No se pudo procesar el archivo: {error}")
            return render(request, "nomina/importar.html", {"formulario": formulario})

        creados = actualizados = 0
        for fila in validos:
            _, nuevo = Empleado.objects.update_or_create(
                empresa=empresa, cedula=fila["cedula"],
                defaults={"nombre": fila["nombre"], "salario": fila["salario"],
                          "fecha_ingreso": fila["fecha_ingreso"], "activo": True})
            creados += nuevo
            actualizados += not nuevo

        if creados or actualizados:
            messages.success(request, f"{creados} empleado(s) nuevo(s) y "
                                      f"{actualizados} actualizado(s).")
        for error in errores[:15]:
            messages.warning(request, error)
        if errores:
            messages.info(request, f"{len(errores)} fila(s) con error no se importaron.")
        if creados or actualizados:
            return redirect("nomina:panel")
    return render(request, "nomina/importar.html", {"formulario": formulario})


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

    # P8.8: novedades del mes agrupadas por empleado
    novedades = defaultdict(list)
    for novedad in NovedadNomina.objects.de_empresa(empresa).filter(anio=anio, mes=mes):
        novedades[novedad.empleado_id].append(novedad)

    try:
        resultado = liquidar_mes(empresa, empleados, anio, mes, dict(novedades))
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
        messages.success(request, f"Borrador {liquidacion.anio}-{liquidacion.mes:02d} "
                                  "aprobado para la causación contable. La liquidación "
                                  "oficial, la nómina electrónica y la PILA van por tu "
                                  "software de nómina.")
    else:
        messages.info(request, "Liquidación rechazada: corrige la planta o los "
                               "parámetros y vuelve a liquidar (elimínala en el admin).")
    return redirect("nomina:detalle", pk=pk)
