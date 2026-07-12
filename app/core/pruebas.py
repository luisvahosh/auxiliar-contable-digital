"""Base de pruebas: un usuario admin logueado en la empresa beta (LEARNWAY).
Desde el §12, ninguna vista de negocio responde sin sesión + membresía."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Empresa, Membresia


class CasoConEmpresa(TestCase):
    rol = "admin"

    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")
        Usuario = get_user_model()
        self.usuario = Usuario.objects.create_user(
            username="auxiliar@learnway.example.com",
            email="auxiliar@learnway.example.com",
            password="clave-larga-de-pruebas-123",
        )
        Membresia.objects.create(usuario=self.usuario, empresa=self.empresa,
                                 rol=self.rol)
        self.client.force_login(self.usuario)
