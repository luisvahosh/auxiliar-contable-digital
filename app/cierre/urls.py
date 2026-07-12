from django.urls import path

from . import views

app_name = "cierre"

urlpatterns = [
    path("", views.cierre, name="cierre"),
    path("paquete/", views.descargar_paquete, name="paquete"),
]
