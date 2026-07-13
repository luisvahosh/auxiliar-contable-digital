from django.contrib import admin

from .models import CajaMenor, GastoCajaMenor, ReembolsoCajaMenor


@admin.register(CajaMenor)
class CajaMenorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "monto_fijo", "activa", "empresa")
    list_filter = ("activa", "empresa")


@admin.register(GastoCajaMenor)
class GastoCajaMenorAdmin(admin.ModelAdmin):
    list_display = ("concepto", "caja", "fecha", "total", "reembolso", "empresa")
    list_filter = ("empresa",)


@admin.register(ReembolsoCajaMenor)
class ReembolsoCajaMenorAdmin(admin.ModelAdmin):
    list_display = ("caja", "fecha", "estado", "total", "empresa")
    list_filter = ("estado", "empresa")
    readonly_fields = ("asiento",)
