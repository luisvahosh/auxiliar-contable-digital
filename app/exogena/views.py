import csv
import io
from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from .logica import formato_1001, formato_1007


def _anio(request):
    try:
        return int(request.GET.get("anio", date.today().year - 1))
    except ValueError:
        return date.today().year - 1


def panel(request):
    empresa = request.empresa
    anio = _anio(request)
    f1001 = formato_1001(empresa, anio)
    f1007 = formato_1007(empresa, anio)
    return render(request, "exogena/panel.html", {
        "anio": anio,
        "anios": range(date.today().year, date.today().year - 6, -1),
        "f1001": f1001,
        "f1007": f1007,
    })


def _csv(nombre, encabezados, filas):
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    respuesta = HttpResponse(salida.getvalue().encode("utf-8-sig"),
                            content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def exportar_1001(request):
    anio = _anio(request)
    datos = formato_1001(request.empresa, anio)
    filas = [[f["tipo_doc"], f["nit"], f["nombre"], f["concepto"],
              f"{f['base']:.0f}", f"{f['retencion']:.0f}"] for f in datos["filas"]]
    return _csv(f"exogena-1001-{anio}.csv",
                ["TIPO DOC", "NIT/CEDULA", "NOMBRE O RAZON SOCIAL", "CONCEPTO",
                 "PAGO O ABONO EN CUENTA", "RETENCION PRACTICADA"], filas)


def exportar_1007(request):
    anio = _anio(request)
    datos = formato_1007(request.empresa, anio)
    filas = [[f["tipo_doc"], f["nit"], f["nombre"], f["concepto"],
              f"{f['ingreso']:.0f}"] for f in datos["filas"]]
    return _csv(f"exogena-1007-{anio}.csv",
                ["TIPO DOC", "NIT/CEDULA", "NOMBRE O RAZON SOCIAL", "CONCEPTO",
                 "INGRESO RECIBIDO"], filas)
