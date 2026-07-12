from django import forms
from django.core.exceptions import ValidationError

TAMANO_MAXIMO = 2 * 1024 * 1024


class FormularioSubirExtracto(forms.Form):
    archivo = forms.FileField(
        label="Extracto bancario en CSV",
        help_text="Formato: fecha;descripcion;valor — abonos en positivo, "
                  "cargos en negativo. Máximo 2 MB. (El PDF llegará después.)",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith(".csv"):
            raise ValidationError("El archivo debe tener extensión .csv.")
        if archivo.size > TAMANO_MAXIMO:
            raise ValidationError("El archivo supera el tamaño máximo de 2 MB.")
        return archivo
