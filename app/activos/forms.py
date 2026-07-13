from datetime import date

from django import forms

from .models import ActivoFijo


class FormularioActivo(forms.ModelForm):
    class Meta:
        model = ActivoFijo
        fields = ["nombre", "categoria", "fecha_adquisicion", "costo",
                  "valor_residual", "activo"]
        widgets = {"fecha_adquisicion": forms.DateInput(attrs={"type": "date"})}

    def clean_costo(self):
        costo = self.cleaned_data["costo"]
        if costo <= 0:
            raise forms.ValidationError("El costo debe ser mayor que cero.")
        return costo

    def clean(self):
        datos = super().clean()
        costo, residual = datos.get("costo"), datos.get("valor_residual")
        if costo is not None and residual is not None and residual >= costo:
            raise forms.ValidationError("El valor residual debe ser menor que el costo.")
        return datos


class FormularioDepreciar(forms.Form):
    periodo = forms.CharField(
        label="Mes a depreciar",
        widget=forms.TextInput(attrs={"type": "month"}))

    def clean_periodo(self):
        try:
            anio, mes = map(int, self.cleaned_data["periodo"].split("-"))
            date(anio, mes, 1)
        except (ValueError, TypeError):
            raise forms.ValidationError("Formato AAAA-MM.")
        return anio, mes
