import uuid

from django.db import models


class Empresa(models.Model):
    """Tenant: cada empresa cliente del producto (PLAN.md §12).

    Todo dato de negocio cuelga de una empresa; ninguna query de negocio
    corre sin filtrar por ella. UUID como pk: nunca ids secuenciales en URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nit = models.CharField("NIT", max_length=20, unique=True)
    razon_social = models.CharField("razón social", max_length=200)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return f"{self.razon_social} (NIT {self.nit})"
