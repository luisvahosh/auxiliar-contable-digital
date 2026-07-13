from django.urls import path

from . import views

app_name = "nomina"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("empleado/", views.empleado, name="empleado_nuevo"),
    path("empleado/<uuid:pk>/", views.empleado, name="empleado_editar"),
    path("importar/", views.importar_empleados, name="importar_empleados"),
    path("novedades/", views.novedades, name="novedades"),
    path("novedades/<uuid:pk>/borrar/", views.borrar_novedad, name="borrar_novedad"),
    path("liquidar/", views.liquidar, name="liquidar"),
    path("<uuid:pk>/", views.detalle, name="detalle"),
    path("<uuid:pk>/<str:decision>/", views.decidir, name="decidir"),
]
