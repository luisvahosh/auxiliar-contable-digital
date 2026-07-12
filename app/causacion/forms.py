from django import forms
from django.core.exceptions import ValidationError

from .models import Tercero

TAMANO_MAXIMO = 2 * 1024 * 1024  # las facturas UBL reales pesan pocos KB


class FormularioSubirFactura(forms.Form):
    archivo = forms.FileField(
        label="Archivo XML de la factura",
        help_text="El XML descargado del portal DIAN o recibido del proveedor. Máximo 2 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".xml,text/xml,application/xml"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".xml"):
            raise ValidationError("El archivo debe tener extensión .xml.")
        if archivo.size > TAMANO_MAXIMO:
            raise ValidationError("El archivo supera el tamaño máximo de 2 MB.")
        return archivo


TIPOS_IMAGEN = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
TAMANO_MAXIMO_FOTO = 5 * 1024 * 1024


class FormularioFotoFactura(forms.Form):
    """Paso 1 del flujo P1.10: la foto de la factura de papel."""

    foto = forms.FileField(
        label="Foto de la factura física",
        help_text="JPG, PNG o WebP, máximo 5 MB. En el celular este botón abre la cámara.",
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/webp",
            "capture": "environment",  # cámara trasera en móviles
        }),
    )

    def clean_foto(self):
        foto = self.cleaned_data["foto"]
        if foto.content_type not in TIPOS_IMAGEN:
            raise ValidationError("La foto debe ser JPG, PNG o WebP.")
        if foto.size > TAMANO_MAXIMO_FOTO:
            raise ValidationError("La foto supera el tamaño máximo de 5 MB.")
        return foto


class FormularioFacturaFisica(forms.Form):
    """Paso 2 del flujo P1.10: el usuario confirma campo por campo lo extraído."""

    nit_emisor = forms.CharField(label="NIT o cédula del emisor (solo dígitos, sin DV)",
                                 max_length=20)
    nombre_emisor = forms.CharField(label="Nombre o razón social del emisor", max_length=200)
    tipo_persona = forms.ChoiceField(
        label="Tipo de persona del emisor",
        choices=[("1", "Persona jurídica"), ("2", "Persona natural")])
    numero = forms.CharField(label="Número de la factura", max_length=50)
    fecha = forms.DateField(label="Fecha de emisión",
                            widget=forms.DateInput(attrs={"type": "date"}))
    subtotal = forms.DecimalField(label="Subtotal (antes de IVA)", min_value=0,
                                  max_digits=16, decimal_places=2)
    iva = forms.DecimalField(label="IVA", min_value=0, max_digits=16,
                             decimal_places=2, initial=0)
    total = forms.DecimalField(label="Total de la factura", min_value=0,
                               max_digits=16, decimal_places=2)
    concepto = forms.CharField(label="Concepto (qué se compró)", max_length=200)

    def clean_nit_emisor(self):
        nit = self.cleaned_data["nit_emisor"].strip()
        if not nit.isdigit():
            raise ValidationError("Solo dígitos, sin puntos ni dígito de verificación.")
        return nit

    def clean(self):
        datos = super().clean()
        subtotal, iva, total = (datos.get("subtotal"), datos.get("iva"), datos.get("total"))
        if None not in (subtotal, iva, total) and subtotal + iva != total:
            raise ValidationError(
                f"Los totales no cuadran: subtotal {subtotal} + IVA {iva} ≠ total {total}. "
                "Revisa contra la factura física.")
        return datos


class FormularioReclasificacion(forms.Form):
    """El usuario corrige la cuenta PUC propuesta; retención y asiento se
    recalculan (humano en el circuito, nivel manual)."""

    cuenta = forms.ChoiceField(label="Cuenta PUC correcta")
    motivo = forms.CharField(
        label="¿Por qué la reclasificas? (queda en la explicación)",
        max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        from .clasificacion import CONCEPTOS_RETENCION, cuentas_reclasificables
        super().__init__(*args, **kwargs)
        self.fields["cuenta"].choices = [
            (cuenta, f"{cuenta} — {nombre} (retención: "
                     f"{CONCEPTOS_RETENCION[concepto]['nombre'].lower()})")
            for cuenta, nombre, concepto in cuentas_reclasificables()
        ]


class FormularioTercero(forms.ModelForm):
    """Edición de la calidad tributaria de un tercero, cotejada con su RUT."""

    class Meta:
        model = Tercero
        fields = ["razon_social", "tipo_persona", "declarante",
                  "autorretenedor", "regimen_simple", "verificado"]
