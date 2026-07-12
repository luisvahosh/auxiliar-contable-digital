from django.contrib import admin

from .models import ExtractoBancario, MovimientoBancario


@admin.register(ExtractoBancario)
class ExtractoBancarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "creado")
    list_filter = ("empresa",)


@admin.register(MovimientoBancario)
class MovimientoBancarioAdmin(admin.ModelAdmin):
    list_display = ("fecha", "descripcion", "valor", "sugerencia", "estado", "empresa")
    list_filter = ("estado", "sugerencia", "empresa")
    search_fields = ("descripcion",)
    readonly_fields = ("asiento",)
