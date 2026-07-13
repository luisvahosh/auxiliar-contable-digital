"""Contexto común a todas las plantillas: si el usuario es admin de la empresa
activa (para mostrar/ocultar accesos de administración en la navegación)."""
from .tenancy import rol_en_empresa


def datos_sesion(request):
    es_admin = False
    if getattr(request, "empresa", None) and request.user.is_authenticated:
        es_admin = rol_en_empresa(request, request.empresa) == "admin"
    return {"es_admin_empresa": es_admin}
