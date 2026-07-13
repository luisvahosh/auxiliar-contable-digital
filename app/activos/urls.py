from django.urls import path

from . import views

app_name = "activos"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("activo/", views.activo, name="activo_nuevo"),
    path("activo/<uuid:pk>/", views.activo, name="activo_editar"),
    path("depreciar/", views.depreciar, name="depreciar"),
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/<str:decision>/", views.decidir, name="decidir"),
]
