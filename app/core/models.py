import hashlib
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Empresa(models.Model):
    """Tenant: cada empresa cliente del producto (PLAN.md §12).

    Todo dato de negocio cuelga de una empresa; ninguna query de negocio
    corre sin filtrar por ella. UUID como pk: nunca ids secuenciales en URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nit = models.CharField("NIT", max_length=20, unique=True)
    razon_social = models.CharField("razón social", max_length=200)
    # Alertas del calendario tributario (guía P6.2)
    correo_alertas = models.EmailField(
        "correo para alertas tributarias", blank=True,
        help_text="Vacío = sin alertas por correo")
    dias_anticipacion_alertas = models.PositiveSmallIntegerField(
        "días de anticipación de las alertas", default=5)
    # Recordatorios de cobro a clientes morosos (guía P5.2) — opt-in por tenant
    enviar_recordatorios_cobro = models.BooleanField(
        "enviar recordatorios de cobro", default=False,
        help_text="Correo con el estado de cuenta a clientes con facturas vencidas")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return f"{self.razon_social} (NIT {self.nit})"


ROLES = [
    ("admin", "Administrador de empresa"),
    ("operador", "Operador"),
    ("lectura", "Solo lectura"),
]


class Membresia(models.Model):
    """Vínculo usuario ↔ empresa (PLAN.md §12). Un usuario puede pertenecer a
    varias empresas (plan Contador) pero solo opera una a la vez (sesión)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="membresias")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                related_name="membresias")
    rol = models.CharField(max_length=10, choices=ROLES, default="operador")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "empresa"],
                                    name="membresia_unica"),
        ]
        verbose_name = "membresía"
        verbose_name_plural = "membresías"

    def __str__(self):
        return f"{self.usuario} en {self.empresa} ({self.get_rol_display()})"


VIGENCIA_INVITACION = timedelta(hours=72)


class Invitacion(models.Model):
    """Token de un solo uso para matricular usuarios (PLAN.md §12): aleatorio,
    con expiración de 72 h y guardado hasheado — el token en claro solo existe
    en el enlace enviado."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                related_name="invitaciones")
    correo = models.EmailField("correo del invitado")
    rol = models.CharField(max_length=10, choices=ROLES, default="operador")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expira = models.DateTimeField(editable=False)
    usada_en = models.DateTimeField(null=True, blank=True, editable=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "invitación"
        verbose_name_plural = "invitaciones"

    def __str__(self):
        return f"Invitación a {self.correo} — {self.empresa.razon_social}"

    @staticmethod
    def _hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def crear(cls, empresa, correo, rol="operador"):
        """Devuelve (invitación, token en claro). El claro no se persiste."""
        token = secrets.token_urlsafe(32)
        invitacion = cls.objects.create(
            empresa=empresa, correo=correo, rol=rol,
            token_hash=cls._hash(token),
            expira=timezone.now() + VIGENCIA_INVITACION,
        )
        return invitacion, token

    @classmethod
    def buscar_valida(cls, token):
        """La invitación viva para ese token, o None (sin revelar por qué no)."""
        invitacion = cls.objects.filter(token_hash=cls._hash(token)).first()
        if invitacion and invitacion.usada_en is None and invitacion.expira > timezone.now():
            return invitacion
        return None

    def marcar_usada(self):
        self.usada_en = timezone.now()
        self.save(update_fields=["usada_en"])
