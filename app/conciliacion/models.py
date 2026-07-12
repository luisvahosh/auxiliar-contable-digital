import uuid

from django.db import models

from causacion.models import ConsultasPorEmpresa


class ExtractoBancario(models.Model):
    """Un extracto bancario cargado (CSV por ahora; PDF llegará con P4.5)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.PROTECT,
                                related_name="extractos")
    nombre = models.CharField("nombre del extracto", max_length=120)
    creado = models.DateTimeField(auto_now_add=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["-creado"]
        verbose_name = "extracto bancario"
        verbose_name_plural = "extractos bancarios"

    def __str__(self):
        return self.nombre


class MovimientoBancario(models.Model):
    """Un renglón del extracto, con la sugerencia de cruce del motor."""

    SUGERENCIAS = [
        ("pago_cliente", "Pago de cliente"),
        ("pago_cliente_parcial", "Pago parcial de cliente"),
        ("pago_proveedor", "Pago a proveedor"),
        ("gasto_bancario", "Gasto bancario"),
        ("sin_identificar", "Sin identificar"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("conciliado", "Conciliado"),
        ("excepcion", "Excepción"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.PROTECT,
                                related_name="movimientos_bancarios")
    extracto = models.ForeignKey(ExtractoBancario, on_delete=models.CASCADE,
                                 related_name="movimientos")
    fila = models.PositiveIntegerField("fila en el extracto", default=0)
    fecha = models.DateField()
    descripcion = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=16, decimal_places=2)  # abono +, cargo -

    sugerencia = models.CharField(max_length=25, choices=SUGERENCIAS,
                                  default="sin_identificar")
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    factura_venta = models.ForeignKey("causacion.FacturaVenta", null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name="+")
    factura_compra = models.ForeignKey("causacion.FacturaCompra", null=True, blank=True,
                                       on_delete=models.SET_NULL, related_name="+")
    asiento = models.JSONField("asiento propuesto", default=list)
    explicacion = models.TextField()

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["extracto", "fila"]  # el orden del CSV original
        verbose_name = "movimiento bancario"
        verbose_name_plural = "movimientos bancarios"

    def __str__(self):
        return f"{self.fecha} {self.descripcion[:40]} ({self.valor})"

    @property
    def conciliable(self):
        """Solo se puede conciliar lo que tiene una contrapartida identificada."""
        return self.sugerencia != "sin_identificar"
