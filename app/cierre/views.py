from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .logica import periodos_disponibles, resumen_cierre
from .paquete import construir_paquete


def _empresa_activa(request):
    """Tenant del request: lo resuelve el middleware desde la sesión (§12)."""
    return request.empresa


def _periodo_pedido(request, periodos):
    """?periodo=AAAA-MM válido, o el mes más reciente con documentos."""
    crudo = request.GET.get("periodo", "")
    try:
        anio, mes = map(int, crudo.split("-"))
        return date(anio, mes, 1)
    except ValueError:
        return periodos[0] if periodos else None


def cierre(request):
    empresa = _empresa_activa(request)
    periodos = periodos_disponibles(empresa)
    periodo = _periodo_pedido(request, periodos)
    resumen = resumen_cierre(empresa, periodo.year, periodo.month) if periodo else None
    return render(request, "cierre/cierre.html", {
        "empresa": empresa,
        "periodos": periodos,
        "periodo": periodo,
        "resumen": resumen,
    })


def descargar_paquete(request):
    empresa = _empresa_activa(request)
    periodos = periodos_disponibles(empresa)
    periodo = _periodo_pedido(request, periodos)
    if periodo is None:
        messages.error(request, "No hay documentos registrados aún: nada que empaquetar.")
        return redirect("cierre:cierre")
    nombre, contenido = construir_paquete(empresa, periodo.year, periodo.month)
    respuesta = HttpResponse(contenido, content_type="application/zip")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta
