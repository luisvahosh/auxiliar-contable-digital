from django.urls import path

from . import views

app_name = "conciliacion"

urlpatterns = [
    path("", views.bancos, name="bancos"),
    path("<uuid:pk>/", views.extracto, name="extracto"),
    path("movimiento/<uuid:pk>/conciliar/", views.conciliar, name="conciliar"),
    path("movimiento/<uuid:pk>/excepcion/", views.excepcion, name="excepcion"),
]
