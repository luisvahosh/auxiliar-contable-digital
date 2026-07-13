from django.urls import path

from . import views

app_name = "informes"

urlpatterns = [
    path("", views.balance, name="balance"),
    path("balance.csv", views.exportar_balance, name="exportar_balance"),
    path("resultados/", views.resultados, name="resultados"),
    path("general/", views.general, name="general"),
    path("mayor/<str:cuenta>/", views.mayor, name="mayor"),
]
