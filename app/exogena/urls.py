from django.urls import path

from . import views

app_name = "exogena"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("1001.csv", views.exportar_1001, name="exportar_1001"),
    path("1007.csv", views.exportar_1007, name="exportar_1007"),
]
