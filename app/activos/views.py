from decimal import Decimal

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .calculo import depreciar_mes
from .forms import FormularioActivo, FormularioDepreciar
from .models import ActivoFijo, DepreciacionMensual


def panel(request):
    empresa = request.empresa
    return render(request, "activos/panel.html", {
        "empresa": empresa,
        "activos": ActivoFijo.objects.de_empresa(empresa),
        "depreciaciones": DepreciacionMensual.objects.de_empresa(empresa),
        "formulario_depreciar": FormularioDepreciar(),
    })


def activo(request, pk=None):
    empresa = request.empresa
    instancia = (get_object_or_404(ActivoFijo.objects.de_empresa(empresa), pk=pk)
                 if pk else None)
    formulario = FormularioActivo(request.POST or None, instance=instancia)
    if request.method == "POST" and formulario.is_valid():
        nuevo = formulario.save(commit=False)
        nuevo.empresa = empresa
        nuevo.save()
        messages.success(request, f"Activo «{nuevo.nombre}» guardado.")
        return redirect("activos:panel")
    return render(request, "activos/activo_form.html", {
        "formulario": formulario, "instancia": instancia,
    })


@require_POST
def depreciar(request):
    empresa = request.empresa
    formulario = FormularioDepreciar(request.POST)
    if not formulario.is_valid():
        messages.error(request, "Período inválido (formato AAAA-MM).")
        return redirect("activos:panel")
    anio, mes = formulario.cleaned_data["periodo"]

    if DepreciacionMensual.objects.de_empresa(empresa).filter(anio=anio, mes=mes).exists():
        messages.warning(request, f"La depreciación de {anio}-{mes:02d} ya existe.")
        return redirect("activos:panel")

    activos = list(ActivoFijo.objects.de_empresa(empresa).filter(activo=True))
    resultado = depreciar_mes(empresa, activos, anio, mes)
    if not resultado["detalle"]:
        messages.info(request, "No hay activos por depreciar en ese mes "
                               "(sin activos, o ya totalmente depreciados).")
        return redirect("activos:panel")

    try:
        depreciacion = DepreciacionMensual.objects.create(
            empresa=empresa, anio=anio, mes=mes, detalle=resultado["detalle"],
            total=resultado["total"], asiento=resultado["asiento"],
            explicacion=resultado["explicacion"])
    except IntegrityError:
        messages.warning(request, "Esa depreciación ya existe.")
        return redirect("activos:panel")

    messages.success(request, f"Depreciación de {anio}-{mes:02d} calculada, "
                              "pendiente de tu aprobación.")
    return redirect("activos:detalle", pk=depreciacion.pk)


def detalle(request, pk):
    empresa = request.empresa
    depreciacion = get_object_or_404(
        DepreciacionMensual.objects.de_empresa(empresa), pk=pk)
    renglones = [
        {**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
        for r in depreciacion.asiento
    ]
    return render(request, "activos/detalle.html", {
        "depreciacion": depreciacion,
        "renglones": renglones,
        "total_debitos": sum(r["debito"] for r in renglones),
        "total_creditos": sum(r["credito"] for r in renglones),
    })


@require_POST
def decidir(request, pk, decision):
    empresa = request.empresa
    depreciacion = get_object_or_404(
        DepreciacionMensual.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    if decision == "aprobada":
        with transaction.atomic():
            # Al aprobar, la cuota de cada activo se suma a su acumulada.
            for fila in depreciacion.detalle:
                (ActivoFijo.objects.filter(pk=fila["activo_id"], empresa=empresa)
                 .update(depreciacion_acumulada=Decimal(fila["acumulada_despues"])))
            depreciacion.estado = "aprobada"
            depreciacion.save(update_fields=["estado", "actualizada"])
        messages.success(request, f"Depreciación de {depreciacion.anio}-"
                                  f"{depreciacion.mes:02d} aprobada y aplicada al "
                                  "valor en libros de cada activo.")
    elif decision == "rechazada":
        depreciacion.estado = "rechazada"
        depreciacion.save(update_fields=["estado", "actualizada"])
        messages.info(request, "Depreciación rechazada: no afecta el valor en libros.")
    return redirect("activos:detalle", pk=pk)
