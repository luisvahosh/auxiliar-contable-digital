import uuid

from django.db import models


class ConsultasPorEmpresa(models.Manager):
    """Manager multi-tenant (CLAUDE.md §2): el código de negocio consulta
    SIEMPRE vía .de_empresa(empresa), nunca .all()/.filter() a secas."""

    def de_empresa(self, empresa):
        return self.get_queryset().filter(empresa=empresa)


class FacturaCompra(models.Model):
    """Una factura de compra causada (o en bandeja de revisión):
    electrónica (XML DIAN) o física fotografiada (P1.10)."""

    NIVELES = [
        ("automatica", "Automática"),
        ("sugerida", "Sugerida"),
        ("manual", "Manual"),
    ]
    ORIGENES = [
        ("xml", "XML DIAN"),
        ("foto", "Foto de factura física"),
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
    # P1.10: facturas físicas fotografiadas. Sin CUFE real, el antiduplicado
    # es por NIT+número+fecha (codificado en el campo cufe como FISICA:...).
    origen = models.CharField(max_length=5, choices=ORIGENES, default="xml")
    imagen = models.FileField("foto de la factura física", upload_to="facturas_fisicas",
                              null=True, blank=True)

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


class Tercero(models.Model):
    """Matriz de terceros (guía P3): la calidad tributaria real de cada
    proveedor, tomada de su RUT.

    Se crea automáticamente con la primera factura (a partir del TaxLevelCode
    del XML, quedando "pendiente de verificar"); el auxiliar la corrige contra
    el RUT y la marca verificada. En el cálculo de retenciones, esta matriz
    manda sobre lo que diga el XML.
    """

    TIPOS_PERSONA = [("1", "Persona jurídica"), ("2", "Persona natural")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey("core.Empresa", on_delete=models.CASCADE,
                                related_name="terceros")
    nit = models.CharField("NIT o cédula", max_length=20)
    razon_social = models.CharField("razón social / nombre", max_length=200)
    tipo_persona = models.CharField(max_length=2, choices=TIPOS_PERSONA, default="1")
    declarante = models.BooleanField(
        "declarante de renta", default=True,
        help_text="Si no declara, aplican tarifas de retención más altas")
    autorretenedor = models.BooleanField(
        "autorretenedor", default=False,
        help_text="Se retiene a sí mismo: no se le practica retefuente")
    regimen_simple = models.BooleanField(
        "Régimen Simple de Tributación", default=False,
        help_text="El RST no es sujeto de retención (art. 911 E.T.)")
    verificado = models.BooleanField(
        "verificado contra el RUT", default=False,
        help_text="Marcar cuando la información se haya cotejado con el RUT del tercero")

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = ConsultasPorEmpresa()

    class Meta:
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "nit"],
                                    name="tercero_unico_por_empresa"),
        ]
        verbose_name = "tercero"
        verbose_name_plural = "terceros"

    def __str__(self):
        return f"{self.razon_social} (NIT {self.nit})"

    @property
    def calidades(self):
        etiquetas = []
        if self.regimen_simple:
            etiquetas.append("Régimen Simple")
        if self.autorretenedor:
            etiquetas.append("Autorretenedor")
        etiquetas.append("Declarante" if self.declarante else "No declarante")
        return etiquetas


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
