from django import forms
from django.core.exceptions import ValidationError

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
