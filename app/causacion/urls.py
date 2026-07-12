from django.urls import path

from . import views

app_name = "causacion"

urlpatterns = [
    path("", views.bandeja, name="bandeja"),
    path("subir/", views.subir, name="subir"),
    # Factura física fotografiada (P1.10)
    path("foto/", views.foto, name="foto"),
    path("foto/causar/", views.foto_causar, name="foto_causar"),
    # Ventas (P2) — antes de <uuid:pk> para que "ventas" no se confunda con un id
    path("ventas/", views.bandeja_ventas, name="bandeja_ventas"),
    path("ventas/<uuid:pk>/", views.detalle_venta, name="detalle_venta"),
    path("ventas/<uuid:pk>/aprobar/", views.aprobar_venta, name="aprobar_venta"),
    path("ventas/<uuid:pk>/rechazar/", views.rechazar_venta, name="rechazar_venta"),
    path("ventas/<uuid:pk>/siigo.csv", views.exportar_siigo_venta, name="exportar_siigo_venta"),
    path("ventas/<uuid:pk>/enviar-alegra/", views.enviar_alegra_venta, name="enviar_alegra_venta"),
    # Conexiones contables por empresa
    path("conexiones/", views.conexiones, name="conexiones"),
    # Cartera (P5.1)
    path("cartera/", views.cartera, name="cartera"),
    # Matriz de terceros (P3)
    path("terceros/", views.terceros, name="terceros"),
    path("terceros/<uuid:pk>/", views.editar_tercero, name="editar_tercero"),
    # Compras (P1)
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/reclasificar/", views.reclasificar, name="reclasificar"),
    path("<uuid:pk>/aprobar/", views.aprobar, name="aprobar"),
    path("<uuid:pk>/rechazar/", views.rechazar, name="rechazar"),
    path("<uuid:pk>/siigo.csv", views.exportar_siigo, name="exportar_siigo"),
    path("<uuid:pk>/enviar-alegra/", views.enviar_alegra, name="enviar_alegra"),
]
