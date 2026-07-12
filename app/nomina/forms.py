from datetime import date

from django import forms

from .models import Empleado


class FormularioEmpleado(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = ["nombre", "cedula", "salario", "fecha_ingreso", "activo"]
        widgets = {"fecha_ingreso": forms.DateInput(attrs={"type": "date"})}

    def clean_cedula(self):
        cedula = self.cleaned_data["cedula"].strip()
        if not cedula.isdigit():
            raise forms.ValidationError("Solo dígitos, sin puntos.")
        return cedula

    def clean_salario(self):
        salario = self.cleaned_data["salario"]
        if salario <= 0:
            raise forms.ValidationError("El salario debe ser mayor que cero.")
        return salario


class FormularioLiquidar(forms.Form):
    periodo = forms.CharField(
        label="Mes a liquidar",
        initial=lambda: date.today().strftime("%Y-%m"),
        widget=forms.TextInput(attrs={"type": "month"}))

    def clean_periodo(self):
        crudo = self.cleaned_data["periodo"]
        try:
            anio, mes = map(int, crudo.split("-"))
            date(anio, mes, 1)
        except (ValueError, TypeError):
            raise forms.ValidationError("Formato AAAA-MM.")
        return anio, mes
