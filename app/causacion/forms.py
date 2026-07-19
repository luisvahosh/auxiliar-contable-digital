from django import forms
from django.core.exceptions import ValidationError

from .models import BuzonCorreo, Tercero


class FormularioBuzon(forms.ModelForm):
    """Configuración del buzón de correo de la empresa."""

    clave = forms.CharField(
        label="Contraseña (o contraseña de aplicación)",
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "off"}),
        required=False,
        help_text="Con Gmail/Outlook con verificación en dos pasos, usa una "
                  "contraseña de aplicación. Déjala vacía para no cambiarla.")

    class Meta:
        model = BuzonCorreo
        fields = ["servidor", "puerto", "usuario", "carpeta", "activo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La clave es obligatoria solo al crear (no al editar sin cambiarla)
        if self.instance and self.instance.pk:
            self.fields["clave"].help_text += " (ya hay una guardada)."

    def clean(self):
        datos = super().clean()
        if not (self.instance and self.instance.pk) and not datos.get("clave"):
            self.add_error("clave", "La contraseña es obligatoria al configurar el buzón.")
        return datos

TAMANO_MAXIMO = 10 * 1024 * 1024  # el XML pesa poco, pero un PDF con logos sí crece

# XML pelado, ZIP de la DIAN, o el PDF/HTML si trae el XML embebido dentro.
from .extraer import EXTENSIONES as EXTENSIONES_FACTURA


class FormularioSubirFactura(forms.Form):
    archivo = forms.FileField(
        label="Archivo de la factura (XML, ZIP, PDF o HTML)",
        help_text="El XML de la DIAN o del proveedor. También sirve el ZIP, o el "
                  "PDF/HTML de la factura si trae el XML adentro. Máximo 10 MB.",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".xml,.zip,.pdf,.html,.htm"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(EXTENSIONES_FACTURA):
            raise ValidationError("El archivo debe ser XML, ZIP, PDF o HTML.")
        if archivo.size > TAMANO_MAXIMO:
            raise ValidationError("El archivo supera el tamaño máximo de 10 MB.")
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


class FormularioConexionAlegra(forms.Form):
    """Credenciales de la cuenta Alegra de la empresa (panel de conexiones)."""

    usuario = forms.EmailField(
        label="Correo de la cuenta Alegra",
        widget=forms.EmailInput(attrs={"autocomplete": "off"}))
    token = forms.CharField(
        label="Token de la API",
        max_length=200,
        help_text="Se genera en Alegra → Configuración → Integraciones → API.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}))


class FormularioSubirPUC(forms.Form):
    """Carga del plan de cuentas completo de la empresa (CSV o Excel)."""

    archivo = forms.FileField(
        label="Archivo del PUC (CSV o Excel)",
        help_text="Exporta el plan de cuentas desde tu software contable. Debe "
                  "tener una columna con el código y otra con el nombre. Máx. 10 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx,.xlsm,.txt"}))
    reemplazar = forms.BooleanField(
        label="Reemplazar el PUC que ya está cargado (borra el anterior)",
        required=False)

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith((".csv", ".xlsx", ".xlsm", ".txt")):
            raise ValidationError("El archivo debe ser CSV o Excel (.xlsx).")
        if archivo.size > 10 * 1024 * 1024:
            raise ValidationError("El archivo supera el tamaño máximo de 10 MB.")
        return archivo


class FormularioReclasificacion(forms.Form):
    """El usuario corrige la cuenta PUC propuesta; retención y asiento se
    recalculan (humano en el circuito, nivel manual). Puede elegir CUALQUIER
    cuenta auxiliar de su PUC y, si quiere, dejar la regla amarrada al tercero."""

    cuenta = forms.CharField(
        label="Cuenta PUC correcta (código)", max_length=20,
        help_text="Escribe el código; te sugiere las cuentas de tu PUC "
                  "(incluidas las auxiliares, ej. 51103505).")
    concepto = forms.ChoiceField(
        label="Concepto de retención", required=False,
        help_text="Déjalo en «según la cuenta» si eliges una de las cuentas "
                  "sugeridas por la app; para una auxiliar de tu PUC, elígelo.")
    recordar = forms.BooleanField(
        label="Recordar esta cuenta y concepto para este proveedor "
              "(las próximas facturas suyas se causarán así)",
        required=False)
    motivo = forms.CharField(
        label="¿Por qué la reclasificas? (queda en la explicación)",
        max_length=200, required=False)

    def __init__(self, *args, plan=None, sugeridas=None, **kwargs):
        from .parametros import CONCEPTOS_RETENCION
        super().__init__(*args, **kwargs)
        self.sugeridas = sugeridas or []
        self.fields["cuenta"].widget.attrs["list"] = "puc-codigos"
        self.fields["concepto"].choices = [("", "— según la cuenta sugerida —")] + [
            (clave, datos["nombre"]) for clave, datos in CONCEPTOS_RETENCION.items()]


class FormularioTercero(forms.ModelForm):
    """Edición de la calidad tributaria de un tercero y de la regla de causación
    que el contador le amarra (cuenta de gasto fija + concepto de retención)."""

    class Meta:
        model = Tercero
        fields = ["razon_social", "tipo_persona", "declarante",
                  "autorretenedor", "regimen_simple", "verificado",
                  "cuenta_gasto", "concepto_retencion"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuenta_gasto"].widget.attrs["list"] = "puc-codigos"

    def clean(self):
        datos = super().clean()
        # La cuenta fija no sirve de nada sin concepto de retención: avisar.
        if datos.get("cuenta_gasto") and not datos.get("concepto_retencion"):
            self.add_error("concepto_retencion",
                           "Si fijas una cuenta para el proveedor, elige también "
                           "el concepto de retención con el que se causa.")
        return datos
