from django.contrib import admin

from .models import FacturaCompra, MapeoCuentaAlegra


@admin.register(FacturaCompra)
class FacturaCompraAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre_emisor", "fecha_emision", "total",
                    "cuenta_puc", "nivel", "estado", "empresa")
    list_filter = ("estado", "nivel", "empresa")
    search_fields = ("numero", "nombre_emisor", "nit_emisor", "cufe")
    readonly_fields = ("cufe", "asiento", "xml_crudo", "creada", "actualizada")


@admin.register(MapeoCuentaAlegra)
class MapeoCuentaAlegraAdmin(admin.ModelAdmin):
    list_display = ("cuenta_puc", "id_alegra", "nombre_alegra", "empresa")
    list_filter = ("empresa",)
    search_fields = ("cuenta_puc", "nombre_alegra")
