from django.contrib.auth import views as vistas_auth
from django.urls import path

from . import views
from .forms import FormularioLogin

app_name = "core"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", vistas_auth.LoginView.as_view(
        template_name="core/login.html",
        authentication_form=FormularioLogin,
        redirect_authenticated_user=True,
    ), name="login"),
    path("salir/", vistas_auth.LogoutView.as_view(), name="logout"),
    path("registro/<str:token>/", views.registro, name="registro"),
    path("empresas/", views.empresas, name="empresas"),
    path("empresas/cambiar/", views.cambiar, name="cambiar_empresa"),
    path("empresas/invitar/", views.invitar, name="invitar"),
    path("sin-empresa/", views.sin_empresa, name="sin_empresa"),
]
