from django import forms
from django.core.exceptions import ValidationError

TAMANO_MAXIMO = 2 * 1024 * 1024


class FormularioSubirExtracto(forms.Form):
    archivo = forms.FileField(
        label="Extracto bancario (CSV o PDF)",
        help_text="CSV: fecha;descripcion;valor — abonos en positivo, cargos en "
                  "negativo. PDF: el de texto que descarga el portal del banco. "
                  "Máximo 2 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,.pdf,text/csv,application/pdf"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if not archivo.name.lower().endswith((".csv", ".pdf")):
            raise ValidationError("El archivo debe ser .csv o .pdf.")
        if archivo.size > TAMANO_MAXIMO:
            raise ValidationError("El archivo supera el tamaño máximo de 2 MB.")
        return archivo
