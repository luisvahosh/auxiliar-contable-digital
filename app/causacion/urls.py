from django.urls import path

from . import views

app_name = "causacion"

urlpatterns = [
    path("", views.bandeja, name="bandeja"),
    path("subir/", views.subir, name="subir"),
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/aprobar/", views.aprobar, name="aprobar"),
    path("<uuid:pk>/rechazar/", views.rechazar, name="rechazar"),
]
