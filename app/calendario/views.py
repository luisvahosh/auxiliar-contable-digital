from django.shortcuts import render

from .logica import alertas_de, vencimientos_de


def calendario(request):
    empresa = request.empresa  # lo resuelve el middleware desde la sesión (§12)
    items = vencimientos_de(empresa)
    alertas = alertas_de(empresa)
    return render(request, "calendario/calendario.html", {
        "empresa": empresa,
        "items": items,
        "alertas": alertas,
        "digito": empresa.nit.strip()[-1],
    })
