from datetime import date

from django import forms

from causacion.plan_cuentas import CATEGORIAS_CAJA_MENOR

from .models import CajaMenor, GastoCajaMenor


class FormularioCaja(forms.ModelForm):
    class Meta:
        model = CajaMenor
        fields = ["nombre", "responsable", "monto_fijo", "activa"]

    def clean_monto_fijo(self):
        monto = self.cleaned_data["monto_fijo"]
        if monto <= 0:
            raise forms.ValidationError("El monto del fondo debe ser mayor que cero.")
        return monto


class FormularioGasto(forms.ModelForm):
    categoria = forms.ChoiceField(label="Categoría", choices=CATEGORIAS_CAJA_MENOR)

    class Meta:
        model = GastoCajaMenor
        fields = ["fecha", "categoria", "concepto", "base", "iva"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, caja=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.caja = caja
        self.fields["fecha"].initial = date.today

    def clean_base(self):
        base = self.cleaned_data["base"]
        if base <= 0:
            raise forms.ValidationError("El valor debe ser mayor que cero.")
        return base

    def clean(self):
        datos = super().clean()
        base = datos.get("base") or 0
        iva = datos.get("iva") or 0
        total = base + iva
        datos["total"] = total
        # P11.5: no exceder el efectivo disponible del fondo
        if self.caja is not None and total > self.caja.efectivo_disponible:
            raise forms.ValidationError(
                f"El vale (${total:,.0f}) supera el efectivo disponible del fondo "
                f"(${self.caja.efectivo_disponible:,.0f}). Haz un reembolso primero.")
        return datos
