from django.contrib import admin

from .models import FacturaCompra, FacturaVenta, MapeoCuentaAlegra


@admin.register(FacturaVenta)
class FacturaVentaAdmin(admin.ModelAdmin):
    list_display = ("numero", "tipo", "nombre_cliente", "fecha_emision", "total",
                    "retencion_practicada", "estado", "empresa")
    list_filter = ("estado", "tipo", "empresa")
    search_fields = ("numero", "nombre_cliente", "nit_cliente", "cufe")
    readonly_fields = ("cufe", "asiento", "xml_crudo", "creada", "actualizada")


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
