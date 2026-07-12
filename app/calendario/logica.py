"""
Lógica del calendario tributario por NIT (guía P6.1/P6.2).

Cada empresa ve solo las fechas de su último dígito de NIT (más las que
aplican a todos), con el estado y los días faltantes; las alertas usan la
anticipación configurada por la empresa.
"""
from datetime import date, timedelta

from django.db.models import Q

from .models import VencimientoTributario

HORIZONTE_DIAS = 60          # cuánto futuro muestra la página
VENCIDOS_RECIENTES_DIAS = 15  # cuánto pasado reciente muestra (posibles olvidos)


def digito_del_nit(nit):
    """Último dígito del NIT (sin dígito de verificación): define las fechas DIAN."""
    return nit.strip()[-1]


def vencimientos_de(empresa, hoy=None, horizonte=HORIZONTE_DIAS):
    """Vencimientos de ESTA empresa: recientes vencidos + próximos, anotados."""
    hoy = hoy or date.today()
    digito = digito_del_nit(empresa.nit)
    consulta = (VencimientoTributario.objects
                .filter(Q(ultimo_digito=digito) | Q(ultimo_digito=""))
                .filter(fecha__gte=hoy - timedelta(days=VENCIDOS_RECIENTES_DIAS),
                        fecha__lte=hoy + timedelta(days=horizonte)))
    resultado = []
    for vencimiento in consulta:
        dias = (vencimiento.fecha - hoy).days
        if dias < 0:
            estado = "vencido"
        elif dias == 0:
            estado = "hoy"
        else:
            estado = "proximo"
        resultado.append({
            "vencimiento": vencimiento,
            "dias": dias,
            "dias_absolutos": abs(dias),
            "estado": estado,
        })
    return resultado


def alertas_de(empresa, hoy=None):
    """P6.2: lo que vence dentro de la anticipación configurada (incluye hoy)."""
    hoy = hoy or date.today()
    return [
        item for item in vencimientos_de(empresa, hoy)
        if 0 <= item["dias"] <= empresa.dias_anticipacion_alertas
    ]
