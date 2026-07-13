from django.contrib import admin

from .models import ActivoFijo, DepreciacionMensual


@admin.register(ActivoFijo)
class ActivoFijoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "costo", "depreciacion_acumulada",
                    "activo", "empresa")
    list_filter = ("categoria", "activo", "empresa")
    search_fields = ("nombre",)


@admin.register(DepreciacionMensual)
class DepreciacionMensualAdmin(admin.ModelAdmin):
    list_display = ("empresa", "anio", "mes", "estado", "total", "creada")
    list_filter = ("estado", "empresa")
    readonly_fields = ("detalle", "asiento")
