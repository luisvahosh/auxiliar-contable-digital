# Semilla del calendario tributario 2026 (segundo semestre).
#
# OJO: las fechas son ESTIMADAS a partir del patrón DIAN (declaración el mes
# siguiente al período, escalonada por el último dígito del NIT en el orden
# 1,2,…,9,0, saltando fines de semana). Confirmarlas contra el decreto de
# plazos oficial y ajustarlas en el admin antes de confiar en las alertas.
from datetime import date, timedelta

from django.db import migrations

NOTA = "Fecha ESTIMADA — confirmar contra el decreto de plazos y ajustar en el admin"
ORDEN_DIGITOS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]


def _fecha_habil(anio, mes, dia_base, corrimiento):
    fecha = date(anio, mes, dia_base)
    avanzados = 0
    while avanzados < corrimiento or fecha.weekday() >= 5:  # sáb/dom no cuentan
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            avanzados += 1
    return fecha


def sembrar(apps, schema_editor):
    Vencimiento = apps.get_model("calendario", "VencimientoTributario")
    registros = []

    # Retención en la fuente: período mensual, se declara el mes siguiente.
    MESES = {6: "junio", 7: "julio", 8: "agosto", 9: "septiembre",
             10: "octubre", 11: "noviembre"}
    for mes_periodo, nombre_mes in MESES.items():
        mes_declara = mes_periodo + 1
        for posicion, digito in enumerate(ORDEN_DIGITOS):
            registros.append(Vencimiento(
                obligacion="Retención en la fuente",
                periodo=f"{nombre_mes} 2026",
                ultimo_digito=digito,
                fecha=_fecha_habil(2026, mes_declara, 8, posicion),
                nota=NOTA,
            ))

    # IVA bimestral: se declara el mes siguiente al bimestre.
    BIMESTRES = [("mayo–junio 2026", 7), ("julio–agosto 2026", 9),
                 ("septiembre–octubre 2026", 11)]
    for periodo, mes_declara in BIMESTRES:
        for posicion, digito in enumerate(ORDEN_DIGITOS):
            registros.append(Vencimiento(
                obligacion="IVA bimestral",
                periodo=periodo,
                ultimo_digito=digito,
                fecha=_fecha_habil(2026, mes_declara, 8, posicion),
                nota=NOTA,
            ))

    # ReteICA / ICA Bogotá bimestral: fecha única para todos los NIT.
    ICA = [("bimestre 3 (mayo–junio) 2026", date(2026, 7, 17)),
           ("bimestre 4 (julio–agosto) 2026", date(2026, 9, 18)),
           ("bimestre 5 (septiembre–octubre) 2026", date(2026, 11, 13))]
    for periodo, fecha in ICA:
        registros.append(Vencimiento(
            obligacion="ICA Bogotá (y reteICA)",
            periodo=periodo,
            ultimo_digito="",
            fecha=fecha,
            nota=NOTA + " (Secretaría de Hacienda Distrital)",
        ))

    Vencimiento.objects.bulk_create(registros)


def deshacer(apps, schema_editor):
    apps.get_model("calendario", "VencimientoTributario").objects.filter(
        nota__startswith="Fecha ESTIMADA").delete()


class Migration(migrations.Migration):
    dependencies = [("calendario", "0001_initial")]
    operations = [migrations.RunPython(sembrar, deshacer)]
