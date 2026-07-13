import uuid
from decimal import Decimal

from django.db import models

from causacion.models import ConsultasPorEmpresa
from causacion.plan_cuentas import CATEGORIAS_CAJA_MENOR


class CajaMenor(models.Model):
    """Fondo fijo de efectivo para gastos menores (guía P11)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="cajas_menores")
    nombre = models.CharField("nombre del fondo", max_length=120)
    responsable = models.CharField("responsable", max_length=200, blank=True)
    monto_fijo = models.DecimalField("monto del fondo", max_digits=14, decimal_places=2)
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "caja menor"
        verbose_name_plural = "cajas menores"

    def __str__(self):
        return self.nombre

    @property
    def vales_pendientes(self):
        return self.gastos.filter(reembolso__isnull=True)

    @property
    def total_vales_pendientes(self):
        return (self.vales_pendientes.aggregate(
            s=models.Sum("total"))["s"] or Decimal("0"))

    @property
    def efectivo_disponible(self):
        # Fondo fijo: el efectivo baja con cada vale hasta el reembolso.
        return self.monto_fijo - self.total_vales_pendientes


class GastoCajaMenor(models.Model):
    """Un vale de gasto pagado con la caja menor. Se legaliza en un reembolso."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="gastos_caja_menor")
    caja = models.ForeignKey(CajaMenor, on_delete=models.CASCADE, related_name="gastos")
    fecha = models.DateField()
    categoria = models.CharField("categoría", max_length=20,
                                 choices=CATEGORIAS_CAJA_MENOR)  # rol de cuenta
    concepto = models.CharField(max_length=200)
    base = models.DecimalField("valor sin IVA", max_digits=14, decimal_places=2)
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    reembolso = models.ForeignKey("ReembolsoCajaMenor", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="gastos")
    creado = models.DateTimeField(auto_now_add=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["fecha", "creado"]
        verbose_name = "gasto de caja menor"
        verbose_name_plural = "gastos de caja menor"

    def __str__(self):
        return f"{self.concepto} (${self.total})"


class ReembolsoCajaMenor(models.Model):
    """Legalización de los vales pendientes: repone el fondo con su asiento."""

    ESTADOS = [
        ("pendiente", "Pendiente de aprobación"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="reembolsos_caja_menor")
    caja = models.ForeignKey(CajaMenor, on_delete=models.CASCADE,
                             related_name="reembolsos")
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    total = models.DecimalField(max_digits=14, decimal_places=2)
    asiento = models.JSONField(default=list)
    explicacion = models.TextField()
    actualizado = models.DateTimeField(auto_now=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "reembolso de caja menor"
        verbose_name_plural = "reembolsos de caja menor"

    def __str__(self):
        return f"Reembolso {self.caja.nombre} — ${self.total}"
