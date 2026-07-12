from django.contrib import admin

from .models import Empleado, LiquidacionNomina


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cedula", "salario", "fecha_ingreso", "activo", "empresa")
    list_filter = ("activo", "empresa")
    search_fields = ("nombre", "cedula")


@admin.register(LiquidacionNomina)
class LiquidacionNominaAdmin(admin.ModelAdmin):
    list_display = ("empresa", "anio", "mes", "estado", "total_neto", "creada")
    list_filter = ("estado", "empresa")
    readonly_fields = ("detalle", "asiento")
