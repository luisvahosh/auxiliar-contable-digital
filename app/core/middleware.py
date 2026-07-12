"""
Acceso cerrado por defecto (PLAN.md §12): no hay nada visible sin sesión,
y toda vista de negocio corre con la empresa activa en request.empresa.
"""
from django.shortcuts import redirect
from django.urls import reverse

from .tenancy import empresa_activa

# Lo único público: login, registro por token, admin (con su propio login),
# estáticos y soportes en desarrollo.
PREFIJOS_PUBLICOS = ("/login/", "/registro/", "/admin/", "/static/", "/media/")


class AccesoPorEmpresaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.empresa = None
        if request.path.startswith(PREFIJOS_PUBLICOS):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect(f"{reverse('core:login')}?next={request.path}")

        request.empresa = empresa_activa(request)
        rutas_sin_empresa = (reverse("core:sin_empresa"), reverse("core:logout"))
        if request.empresa is None and request.path not in rutas_sin_empresa:
            return redirect("core:sin_empresa")
        return self.get_response(request)
