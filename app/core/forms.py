from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import ROLES, Empresa


class FormularioCrearEmpresa(forms.ModelForm):
    """Alta de empresa por autoservicio: lo mínimo para arrancar; el resto de
    los datos fiscales se completan luego en Configuración."""

    class Meta:
        model = Empresa
        fields = ["razon_social", "nit", "digito_verificacion", "ciudad"]
        error_messages = {
            "nit": {"unique": "Ya existe una empresa con ese NIT en la plataforma."},
        }


class FormularioConfiguracionEmpresa(forms.ModelForm):
    """Datos fiscales de la empresa (panel de configuración)."""

    class Meta:
        model = Empresa
        fields = ["razon_social", "digito_verificacion", "ciudad",
                  "responsable_iva", "regimen_simple", "es_autorretenedor",
                  "es_agente_retencion", "exonerada_parafiscales",
                  "tarifa_ica_por_mil", "correo_alertas",
                  "dias_anticipacion_alertas", "enviar_recordatorios_cobro"]


class FormularioLogin(AuthenticationForm):
    """Login §12: el error jamás revela qué falló (no enumerar usuarios)."""

    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Correo o contraseña incorrectos.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Correo"
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "autofocus": True})
        self.fields["password"].label = "Contraseña"
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password"})


class FormularioRegistro(forms.Form):
    """El invitado define su nombre y contraseña; el correo viene del token."""

    nombre = forms.CharField(
        label="Tu nombre", max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "name"}))
    contrasena = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Mínimo 10 caracteres, no común, no solo números.")
    confirmacion = forms.CharField(
        label="Repite la contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean(self):
        datos = super().clean()
        contrasena, confirmacion = datos.get("contrasena"), datos.get("confirmacion")
        if contrasena and confirmacion and contrasena != confirmacion:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if contrasena:
            validate_password(contrasena)
        return datos


class FormularioToken2FA(forms.Form):
    token = forms.CharField(
        label="Código de la app (o uno de respaldo)",
        min_length=6, max_length=16,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code",
                                      "autofocus": True}))

    def clean_token(self):
        token = self.cleaned_data["token"].strip().replace(" ", "")
        if not token.isalnum():
            raise forms.ValidationError("Solo letras y números.")
        return token


class FormularioInvitacion(forms.Form):
    correo = forms.EmailField(label="Correo del invitado")
    rol = forms.ChoiceField(label="Rol en la empresa", choices=ROLES,
                            initial="operador")
