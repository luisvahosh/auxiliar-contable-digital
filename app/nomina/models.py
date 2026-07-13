import uuid

from django.db import models

from causacion.models import ConsultasPorEmpresa


class Empleado(models.Model):
    """Planta de personal del tenant (guía P8). Contrato laboral ordinario;
    tipos especiales (integral, aprendiz) llegarán después."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="empleados")
    nombre = models.CharField("nombre completo", max_length=200)
    cedula = models.CharField("cédula", max_length=20)
    salario = models.DecimalField("salario mensual", max_digits=14, decimal_places=2)
    fecha_ingreso = models.DateField("fecha de ingreso")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "cedula"],
                                    name="empleado_unico_por_empresa"),
        ]
        verbose_name = "empleado"
        verbose_name_plural = "empleados"

    def __str__(self):
        return f"{self.nombre} (CC {self.cedula})"


# Efecto de cada tipo de novedad sobre la liquidación (guía P8.8):
#   constitutivo   → suma al salario base (afecta deducciones, aportes, provisiones)
#   no_constitutivo→ suma al devengado y al neto, pero NO a la base
#   reduce_base    → resta del salario base (días no trabajados, incapacidad)
#   descuento      → resta solo del neto (préstamos, embargos)
EFECTO_NOVEDAD = {
    "he_diurna": ("Hora extra diurna (25%)", "constitutivo"),
    "he_nocturna": ("Hora extra nocturna (75%)", "constitutivo"),
    "recargo_nocturno": ("Recargo nocturno (35%)", "constitutivo"),
    "dominical_festivo": ("Recargo dominical/festivo (75%)", "constitutivo"),
    "comision": ("Comisiones", "constitutivo"),
    "bono_salarial": ("Bonificación salarial", "constitutivo"),
    "bono_no_salarial": ("Bonificación no salarial", "no_constitutivo"),
    "dias_no_laborados": ("Días no laborados", "reduce_base"),
    "incapacidad": ("Incapacidad (días a cargo de EPS/ARL)", "reduce_base"),
    "prestamo": ("Préstamo / libranza", "descuento"),
    "embargo": ("Embargo / otro descuento", "descuento"),
}


class NovedadNomina(models.Model):
    """Novedad del mes para un empleado (guía P8.8): horas extra, recargos,
    bonos, días no laborados, descuentos. El valor va en pesos; la cantidad
    (horas o días) es informativa. Una liquidación las consume al calcular."""

    TIPOS = [(clave, etiqueta) for clave, (etiqueta, _) in EFECTO_NOVEDAD.items()]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="novedades_nomina")
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE,
                                 related_name="novedades")
    anio = models.PositiveSmallIntegerField("año")
    mes = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.DecimalField("horas o días", max_digits=8, decimal_places=2,
                                   default=0)
    valor = models.DecimalField("valor en pesos", max_digits=14, decimal_places=2)
    descripcion = models.CharField(max_length=200, blank=True)
    creada = models.DateTimeField(auto_now_add=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["empleado", "tipo"]
        verbose_name = "novedad de nómina"
        verbose_name_plural = "novedades de nómina"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.empleado.nombre} ({self.anio}-{self.mes:02d})"

    @property
    def efecto(self):
        return EFECTO_NOVEDAD[self.tipo][1]


class LiquidacionNomina(models.Model):
    """La nómina de un mes: detalle por empleado, totales y asiento —
    pendiente hasta que el humano la apruebe (P8.6)."""

    ESTADOS = [
        ("pendiente", "Pendiente de aprobación"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="liquidaciones_nomina")
    anio = models.PositiveSmallIntegerField("año")
    mes = models.PositiveSmallIntegerField()
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    detalle = models.JSONField("liquidación por empleado", default=list)
    total_devengado = models.DecimalField(max_digits=16, decimal_places=2)
    total_deducciones = models.DecimalField(max_digits=16, decimal_places=2)
    total_neto = models.DecimalField(max_digits=16, decimal_places=2)
    total_aportes_empleador = models.DecimalField(max_digits=16, decimal_places=2)
    total_provisiones = models.DecimalField(max_digits=16, decimal_places=2)
    asiento = models.JSONField(default=list)
    explicacion = models.TextField()
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["-anio", "-mes"]
        constraints = [
            # P8.5: un mes se liquida una sola vez
            models.UniqueConstraint(fields=["empresa", "anio", "mes"],
                                    name="liquidacion_unica_por_mes"),
        ]
        verbose_name = "liquidación de nómina"
        verbose_name_plural = "liquidaciones de nómina"

    def __str__(self):
        return f"Nómina {self.anio}-{self.mes:02d} — {self.empresa.razon_social}"