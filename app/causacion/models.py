import uuid

from django.db import models


class ConsultasPorEmpresa(models.Manager):
    """Manager multi-tenant (CLAUDE.md §2): el código de negocio consulta
    SIEMPRE vía .de_empresa(empresa), nunca .all()/.filter() a secas."""

    def de_empresa(self, empresa):
        return self.get_queryset().filter(empresa=empresa)


class FacturaCompra(models.Model):
    """Una factura electrónica de compra causada (o en bandeja de revisión)."""

    NIVELES = [
        ("automatica", "Automática"),
        ("sugerida", "Sugerida"),
        ("manual", "Manual"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente de aprobación"),
        ("aprobada", "Aprobada"),
        ("rechazada", "Rechazada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.PROTECT,
                                related_name="facturas_compra")
    cufe = models.CharField("CUFE", max_length=100)
    numero = models.CharField("número", max_length=50)
    fecha_emision = models.DateField("fecha de emisión")
    nit_emisor = models.CharField("NIT del emisor", max_length=20)
    nombre_emisor = models.CharField("emisor", max_length=200)
    tipo_persona_emisor = models.CharField(max_length=2)      # "1" jurídica, "2" natural
    responsabilidad_emisor = models.CharField(max_length=10, blank=True)

    subtotal = models.DecimalField(max_digits=16, decimal_places=2)
    iva = models.DecimalField(max_digits=16, decimal_places=2)
    total = models.DecimalField(max_digits=16, decimal_places=2)
    retencion = models.DecimalField("retención en la fuente", max_digits=16,
                                    decimal_places=2, default=0)

    cuenta_puc = models.CharField("cuenta PUC propuesta", max_length=6)
    nombre_cuenta_puc = models.CharField(max_length=120)
    concepto_retencion = models.CharField(max_length=40, blank=True)
    nivel = models.CharField(max_length=12, choices=NIVELES, default="sugerida")
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    explicacion = models.TextField("porqué de la propuesta")
    asiento = models.JSONField("renglones del asiento propuesto", default=list)
    xml_crudo = models.TextField("XML original (soporte)")

    # Destino contable (P1.9): trazabilidad del envío a Alegra.
    id_alegra = models.CharField("id del asiento en Alegra", max_length=30, blank=True, default="")
    enviada_alegra = models.DateTimeField("enviada a Alegra", null=True, blank=True)

    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["-creada"]
        constraints = [
            # Control P1.5: no causar dos veces la misma factura.
            models.UniqueConstraint(fields=["empresa", "cufe"],
                                    name="cufe_unico_por_empresa"),
        ]
        verbose_name = "factura de compra"
        verbose_name_plural = "facturas de compra"

    def __str__(self):
        return f"{self.numero} — {self.nombre_emisor}"

    # Tercero del asiento (unifica el export Siigo/Alegra con FacturaVenta)
    @property
    def nit_tercero(self):
        return self.nit_emisor

    @property
    def nombre_tercero(self):
        return self.nombre_emisor


class FacturaVenta(models.Model):
    """Una factura emitida por la empresa (o su nota crédito), registrada (P2)."""

    TIPOS = [("venta", "Venta"), ("nota_credito", "Nota crédito")]
    ESTADOS = FacturaCompra.ESTADOS

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.PROTECT,
                                related_name="facturas_venta")
    tipo = models.CharField(max_length=15, choices=TIPOS, default="venta")
    factura_original = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT,
        related_name="notas_credito",
        help_text="Venta que reversa esta nota crédito")
    cufe = models.CharField("CUFE", max_length=100)
    numero = models.CharField("número", max_length=50)
    fecha_emision = models.DateField("fecha de emisión")
    nit_cliente = models.CharField("NIT del cliente", max_length=20)
    nombre_cliente = models.CharField("cliente", max_length=200)

    subtotal = models.DecimalField(max_digits=16, decimal_places=2)
    iva = models.DecimalField(max_digits=16, decimal_places=2)
    total = models.DecimalField(max_digits=16, decimal_places=2)
    retencion_practicada = models.DecimalField(
        "retefuente que practicó el cliente", max_digits=16, decimal_places=2, default=0)

    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    explicacion = models.TextField("porqué del registro")
    asiento = models.JSONField("renglones del asiento propuesto", default=list)
    xml_crudo = models.TextField("XML original (soporte)")

    id_alegra = models.CharField("id del asiento en Alegra", max_length=30, blank=True, default="")
    enviada_alegra = models.DateTimeField("enviada a Alegra", null=True, blank=True)

    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["-creada"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "cufe"],
                                    name="cufe_venta_unico_por_empresa"),
        ]
        verbose_name = "factura de venta"
        verbose_name_plural = "facturas de venta"

    def __str__(self):
        return f"{self.numero} — {self.nombre_cliente}"

    @property
    def nit_tercero(self):
        return self.nit_cliente

    @property
    def nombre_tercero(self):
        return self.nombre_cliente


class MapeoCuentaAlegra(models.Model):
    """Equivalencia cuenta PUC local → id de cuenta contable en Alegra.

    El plan de cuentas de Alegra usa ids propios por cuenta; cada empresa
    registra aquí (vía admin, por ahora) el id que le corresponde a cada
    cuenta PUC que usan sus asientos.
    """

    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="mapeos_alegra")
    cuenta_puc = models.CharField("cuenta PUC", max_length=6)
    id_alegra = models.PositiveIntegerField("id de la cuenta en Alegra")
    nombre_alegra = models.CharField("nombre en Alegra", max_length=120, blank=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "cuenta_puc"],
                                    name="mapeo_unico_por_empresa"),
        ]
        verbose_name = "mapeo de cuenta Alegra"
        verbose_name_plural = "mapeos de cuenta Alegra"

    def __str__(self):
        return f"{self.cuenta_puc} → Alegra #{self.id_alegra}"
