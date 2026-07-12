from django.db import models


class VencimientoTributario(models.Model):
    """Una fecha del calendario tributario (guía P6).

    Es información pública, NO por tenant: la misma tabla sirve a todas las
    empresas y cada una ve sus fechas según el último dígito de su NIT.
    Se mantiene desde el admin cuando la DIAN publica el calendario oficial.
    """

    obligacion = models.CharField("obligación", max_length=80)      # p. ej. Retefuente mensual
    periodo = models.CharField("período", max_length=60)            # p. ej. junio 2026
    ultimo_digito = models.CharField(
        "último dígito del NIT", max_length=1, blank=True,
        help_text="Vacío = aplica a todos los NIT")
    fecha = models.DateField("fecha de vencimiento")
    nota = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["fecha", "obligacion"]
        verbose_name = "vencimiento tributario"
        verbose_name_plural = "vencimientos tributarios"

    def __str__(self):
        digito = f" (NIT …{self.ultimo_digito})" if self.ultimo_digito else ""
        return f"{self.obligacion} {self.periodo}{digito}: {self.fecha}"
