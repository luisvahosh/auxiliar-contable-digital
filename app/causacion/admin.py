from django.contrib import admin

from .models import (ConexionContable, CuentaContable, FacturaCompra,
                     FacturaVenta, MapeoCuentaAlegra, Tercero)


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ("empresa", "rol", "codigo", "nombre")
    list_filter = ("empresa",)
    search_fields = ("rol", "codigo", "nombre")


@admin.register(ConexionContable)
class ConexionContableAdmin(admin.ModelAdmin):
    list_display = ("empresa", "proveedor", "usuario", "activa", "actualizada")
    list_filter = ("proveedor", "activa")
    exclude = ("token",)  # el token no se muestra ni edita desde el admin


@admin.register(Tercero)
class TerceroAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "nit", "tipo_persona", "declarante",
                    "autorretenedor", "regimen_simple", "verificado", "empresa")
    list_filter = ("verificado", "declarante", "autorretenedor", "regimen_simple", "empresa")
    search_fields = ("razon_social", "nit")


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
