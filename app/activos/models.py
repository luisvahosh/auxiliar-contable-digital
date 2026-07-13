import uuid

from django.db import models

from causacion.models import ConsultasPorEmpresa

from .parametros import CATEGORIAS, vida_util_meses


class ActivoFijo(models.Model):
    """Un activo fijo del tenant (guía P10). Depreciación en línea recta;
    la acumulada se actualiza al aprobar cada depreciación mensual."""

    CATEGORIAS_CHOICES = [(clave, datos["nombre"]) for clave, datos in CATEGORIAS.items()]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="activos_fijos")
    nombre = models.CharField("nombre del activo", max_length=200)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES)
    fecha_adquisicion = models.DateField("fecha de adquisición")
    costo = models.DecimalField("costo de adquisición", max_digits=16, decimal_places=2)
    valor_residual = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    depreciacion_acumulada = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "activo fijo"
        verbose_name_plural = "activos fijos"

    def __str__(self):
        return self.nombre

    @property
    def valor_depreciable(self):
        return self.costo - self.valor_residual

    @property
    def cuota_mensual(self):
        from decimal import ROUND_HALF_UP, Decimal
        return (self.valor_depreciable / vida_util_meses(self.categoria)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def saldo_por_depreciar(self):
        return self.valor_depreciable - self.depreciacion_acumulada

    @property
    def valor_en_libros(self):
        return self.costo - self.depreciacion_acumulada


class DepreciacionMensual(models.Model):
    """La depreciación de un mes: detalle por activo, total y asiento —
    pendiente hasta que el humano la apruebe."""

    ESTADOS = [
        ("pendiente", "Pendiente de aprobación"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="depreciaciones")
    anio = models.PositiveSmallIntegerField("año")
    mes = models.PositiveSmallIntegerField()
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    detalle = models.JSONField("depreciación por activo", default=list)
    total = models.DecimalField(max_digits=16, decimal_places=2)
    asiento = models.JSONField(default=list)
    explicacion = models.TextField()
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["-anio", "-mes"]
        constraints = [
            # P10.3: un mes se deprecia una sola vez
            models.UniqueConstraint(fields=["empresa", "anio", "mes"],
                                    name="depreciacion_unica_por_mes"),
        ]
        verbose_name = "depreciación mensual"
        verbose_name_plural = "depreciaciones mensuales"

    def __str__(self):
        return f"Depreciación {self.anio}-{self.mes:02d} — {self.empresa.razon_social}"
