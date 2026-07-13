from django.urls import path

from . import views

app_name = "cajamenor"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("nueva/", views.caja_nueva, name="caja_nueva"),
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/reembolsar/", views.reembolsar, name="reembolsar"),
    path("reembolso/<uuid:pk>/", views.reembolso_detalle, name="reembolso"),
    path("reembolso/<uuid:pk>/<str:decision>/", views.decidir, name="decidir"),
]
