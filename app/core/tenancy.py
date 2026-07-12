"""
Resolución del tenant activo (PLAN.md §12): la empresa con la que el usuario
trabaja en esta sesión. Un usuario multi-empresa (plan Contador) cambia con
el selector, pero nunca ve datos de dos empresas a la vez.
"""
from .models import Empresa

CLAVE_SESION = "empresa_activa"


def empresa_activa(request):
    """Empresa activa del usuario autenticado, o None si no tiene membresías."""
    membresias = request.user.membresias.select_related("empresa")

    elegida = request.session.get(CLAVE_SESION)
    if elegida:
        membresia = membresias.filter(empresa_id=elegida).first()
        if membresia:
            return membresia.empresa

    membresia = membresias.order_by("creada").first()
    if membresia:
        request.session[CLAVE_SESION] = str(membresia.empresa_id)
        return membresia.empresa

    # Personal interno (superusuario) sin membresía: opera la primera empresa.
    if request.user.is_superuser:
        return Empresa.objects.order_by("creada").first()
    return None


def cambiar_empresa(request, empresa_id):
    """Cambia la empresa activa SOLO si el usuario pertenece a ella."""
    membresia = request.user.membresias.filter(empresa_id=empresa_id).first()
    if membresia is None:
        return False
    request.session[CLAVE_SESION] = str(membresia.empresa_id)
    return True


def rol_en_empresa(request, empresa):
    membresia = request.user.membresias.filter(empresa=empresa).first()
    if membresia:
        return membresia.rol
    return "admin" if request.user.is_superuser else ""
