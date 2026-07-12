from django.contrib import admin

from .models import Empresa, Invitacion, Membresia


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "nit", "correo_alertas", "creada")
    search_fields = ("razon_social", "nit")


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "rol", "creada")
    list_filter = ("rol", "empresa")


@admin.register(Invitacion)
class InvitacionAdmin(admin.ModelAdmin):
    list_display = ("correo", "empresa", "rol", "expira", "usada_en")
    list_filter = ("empresa",)
    readonly_fields = ("token_hash", "expira", "usada_en")
