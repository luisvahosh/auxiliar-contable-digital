import csv
import io
from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from .logica import (
    balance_comprobacion,
    balance_general,
    estado_resultados,
    libro_mayor,
)


def _periodo(request):
    hoy = date.today()
    try:
        anio = int(request.GET.get("anio", hoy.year))
    except ValueError:
        anio = hoy.year
    mes = request.GET.get("mes", "")
    mes = int(mes) if mes.isdigit() and 1 <= int(mes) <= 12 else None
    return anio, mes


def _contexto_periodo(request):
    anio, mes = _periodo(request)
    return {
        "anio": anio, "mes": mes,
        "anios": range(date.today().year, date.today().year - 6, -1),
        "meses": range(1, 13),
    }


def balance(request):
    anio, mes = _periodo(request)
    return render(request, "informes/balance.html", {
        "balance": balance_comprobacion(request.empresa, anio, mes),
        **_contexto_periodo(request),
    })


def resultados(request):
    anio, mes = _periodo(request)
    return render(request, "informes/resultados.html", {
        "er": estado_resultados(request.empresa, anio, mes),
        **_contexto_periodo(request),
    })


def general(request):
    anio, mes = _periodo(request)
    return render(request, "informes/general.html", {
        "bg": balance_general(request.empresa, anio, mes),
        **_contexto_periodo(request),
    })


def mayor(request, cuenta):
    anio, mes = _periodo(request)
    return render(request, "informes/mayor.html", {
        "cuenta": cuenta,
        "filas": libro_mayor(request.empresa, cuenta, anio, mes),
        **_contexto_periodo(request),
    })


def exportar_balance(request):
    anio, mes = _periodo(request)
    datos = balance_comprobacion(request.empresa, anio, mes)
    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    w.writerow(["CUENTA", "NOMBRE", "DEBITO", "CREDITO", "SALDO"])
    for f in datos["filas"]:
        w.writerow([f["cuenta"], f["nombre"], f"{f['debito']:.0f}",
                    f"{f['credito']:.0f}", f"{f['saldo']:.0f}"])
    w.writerow(["", "TOTALES", f"{datos['total_debito']:.0f}",
                f"{datos['total_credito']:.0f}", ""])
    periodo = f"{anio}" + (f"-{mes:02d}" if mes else "")
    respuesta = HttpResponse(salida.getvalue().encode("utf-8-sig"),
                            content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="balance-{periodo}.csv"'
    return respuesta
