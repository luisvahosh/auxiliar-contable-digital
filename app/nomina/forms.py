from datetime import date

from django import forms

from .models import Empleado, NovedadNomina


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


class FormularioNovedad(forms.ModelForm):
    periodo = forms.CharField(
        label="Mes de la novedad",
        widget=forms.TextInput(attrs={"type": "month"}))

    class Meta:
        model = NovedadNomina
        fields = ["empleado", "tipo", "cantidad", "valor", "descripcion"]

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.fields["empleado"].queryset = Empleado.objects.de_empresa(
                empresa).filter(activo=True)

    def clean_periodo(self):
        try:
            anio, mes = map(int, self.cleaned_data["periodo"].split("-"))
            date(anio, mes, 1)
        except (ValueError, TypeError):
            raise forms.ValidationError("Formato AAAA-MM.")
        return anio, mes

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor <= 0:
            raise forms.ValidationError("El valor en pesos debe ser mayor que cero.")
        return valor


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
