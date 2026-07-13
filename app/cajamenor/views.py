from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from causacion.plan_cuentas import plan_de_empresa

from .forms import FormularioCaja, FormularioGasto
from .logica import asiento_constitucion, asiento_reembolso
from .models import CajaMenor, GastoCajaMenor, ReembolsoCajaMenor


def panel(request):
    empresa = request.empresa
    return render(request, "cajamenor/panel.html", {
        "cajas": CajaMenor.objects.de_empresa(empresa),
    })


def caja_nueva(request):
    empresa = request.empresa
    formulario = FormularioCaja(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        caja = formulario.save(commit=False)
        caja.empresa = empresa
        caja.save()
        messages.success(request, f"Fondo «{caja.nombre}» constituido por "
                                  f"${caja.monto_fijo:,.0f}.")
        return redirect("cajamenor:detalle", pk=caja.pk)
    return render(request, "cajamenor/caja_form.html", {"formulario": formulario})


def detalle(request, pk):
    empresa = request.empresa
    caja = get_object_or_404(CajaMenor.objects.de_empresa(empresa), pk=pk)
    plan = plan_de_empresa(empresa)
    formulario = FormularioGasto(request.POST or None, caja=caja)
    if request.method == "POST" and formulario.is_valid():
        gasto = formulario.save(commit=False)
        gasto.empresa = empresa
        gasto.caja = caja
        gasto.total = formulario.cleaned_data["total"]
        gasto.save()
        messages.success(request, f"Vale «{gasto.concepto}» registrado.")
        return redirect("cajamenor:detalle", pk=caja.pk)

    def renglones(asiento):
        return [{**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
                for r in asiento]

    return render(request, "cajamenor/detalle.html", {
        "caja": caja,
        "formulario": formulario,
        "vales": caja.vales_pendientes,
        "reembolsos": caja.reembolsos.all(),
        "asiento_constitucion": renglones(asiento_constitucion(caja, plan)),
    })


@require_POST
def reembolsar(request, pk):
    empresa = request.empresa
    caja = get_object_or_404(CajaMenor.objects.de_empresa(empresa), pk=pk)
    gastos = list(caja.vales_pendientes)
    if not gastos:
        messages.info(request, "No hay vales pendientes por reembolsar.")
        return redirect("cajamenor:detalle", pk=caja.pk)

    plan = plan_de_empresa(empresa)
    reembolso = ReembolsoCajaMenor(empresa=empresa, caja=caja,
                                   total=sum(g.total for g in gastos))
    renglones, explicacion = asiento_reembolso(reembolso, gastos, plan)
    reembolso.asiento = renglones
    reembolso.explicacion = explicacion
    reembolso.save()
    # Vincular los vales a este reembolso (quedan legalizados al aprobar)
    for gasto in gastos:
        gasto.reembolso = reembolso
        gasto.save(update_fields=["reembolso"])
    messages.success(request, f"Reembolso por ${reembolso.total:,.0f} creado, "
                              "pendiente de tu aprobación.")
    return redirect("cajamenor:reembolso", pk=reembolso.pk)


def reembolso_detalle(request, pk):
    empresa = request.empresa
    reembolso = get_object_or_404(
        ReembolsoCajaMenor.objects.de_empresa(empresa), pk=pk)
    renglones = [
        {**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
        for r in reembolso.asiento
    ]
    return render(request, "cajamenor/reembolso.html", {
        "reembolso": reembolso,
        "renglones": renglones,
        "total_debitos": sum(r["debito"] for r in renglones),
        "total_creditos": sum(r["credito"] for r in renglones),
    })


@require_POST
def decidir(request, pk, decision):
    empresa = request.empresa
    reembolso = get_object_or_404(
        ReembolsoCajaMenor.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    if decision == "aprobado":
        reembolso.estado = "aprobado"
        reembolso.save(update_fields=["estado", "actualizado"])
        messages.success(request, f"Reembolso aprobado. El fondo «{reembolso.caja.nombre}» "
                                  "vuelve a su monto fijo.")
    elif decision == "rechazado":
        # Al rechazar, los vales vuelven a quedar pendientes (se desvinculan)
        reembolso.gastos.update(reembolso=None)
        reembolso.estado = "rechazado"
        reembolso.save(update_fields=["estado", "actualizado"])
        messages.info(request, "Reembolso rechazado: los vales vuelven a pendientes.")
    return redirect("cajamenor:reembolso", pk=reembolso.pk)
