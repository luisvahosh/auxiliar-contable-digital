from django.contrib import admin

from .models import VencimientoTributario


@admin.register(VencimientoTributario)
class VencimientoTributarioAdmin(admin.ModelAdmin):
    list_display = ("obligacion", "periodo", "ultimo_digito", "fecha", "nota")
    list_filter = ("obligacion",)
    search_fields = ("obligacion", "periodo")
