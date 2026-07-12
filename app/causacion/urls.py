from django.urls import path

from . import views

app_name = "causacion"

urlpatterns = [
    path("", views.bandeja, name="bandeja"),
    path("subir/", views.subir, name="subir"),
    # Ventas (P2) — antes de <uuid:pk> para que "ventas" no se confunda con un id
    path("ventas/", views.bandeja_ventas, name="bandeja_ventas"),
    path("ventas/<uuid:pk>/", views.detalle_venta, name="detalle_venta"),
    path("ventas/<uuid:pk>/aprobar/", views.aprobar_venta, name="aprobar_venta"),
    path("ventas/<uuid:pk>/rechazar/", views.rechazar_venta, name="rechazar_venta"),
    path("ventas/<uuid:pk>/siigo.csv", views.exportar_siigo_venta, name="exportar_siigo_venta"),
    path("ventas/<uuid:pk>/enviar-alegra/", views.enviar_alegra_venta, name="enviar_alegra_venta"),
    # Compras (P1)
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/aprobar/", views.aprobar, name="aprobar"),
    path("<uuid:pk>/rechazar/", views.rechazar, name="rechazar"),
    path("<uuid:pk>/siigo.csv", views.exportar_siigo, name="exportar_siigo"),
    path("<uuid:pk>/enviar-alegra/", views.enviar_alegra, name="enviar_alegra"),
]
