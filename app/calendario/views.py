from django.shortcuts import render

from core.models import Empresa

from .logica import alertas_de, vencimientos_de


def _empresa_activa(request):
    return Empresa.objects.order_by("creada").first()


def calendario(request):
    empresa = _empresa_activa(request)
    items = vencimientos_de(empresa)
    alertas = alertas_de(empresa)
    return render(request, "calendario/calendario.html", {
        "empresa": empresa,
        "items": items,
        "alertas": alertas,
        "digito": empresa.nit.strip()[-1],
    })
