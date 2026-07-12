from django.urls import path

from . import views

app_name = "nomina"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("empleado/", views.empleado, name="empleado_nuevo"),
    path("empleado/<uuid:pk>/", views.empleado, name="empleado_editar"),
    path("liquidar/", views.liquidar, name="liquidar"),
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/<str:decision>/", views.decidir, name="decidir"),
]
