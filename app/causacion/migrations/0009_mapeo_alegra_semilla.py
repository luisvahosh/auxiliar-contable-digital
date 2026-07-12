# Semilla del mapeo cuenta PUC -> catálogo Alegra para la empresa beta.
#
# Los ids corresponden al catálogo NIIF de la cuenta Alegra de la beta cero
# (validados por API en julio 2026: todos aceptan movimientos, blocked=no).
# Sin esta semilla, un ambiente nuevo (p. ej. el VPS) rechaza el envío a
# Alegra con "faltan cuentas por mapear". Editable en el admin.
from django.db import migrations

MAPEO = {
    "5110":   (5202, "Otros honorarios"),
    "240802": (5101, "Impuesto a las ventas descontable"),
    "236515": (5112, "Retenciones honorarios y comisiones 10% por pagar"),
    "2335":   (5070, "Cuentas por pagar a proveedores nacionales"),
    "2205":   (5070, "Cuentas por pagar a proveedores nacionales"),
    "236540": (5120, "Retenciones compra 2.5% por pagar"),
    "236525": (5115, "Retenciones servicios 4% por pagar"),
    "236530": (5118, "Retenciones arriendo 3.5% por pagar"),
    "1435":   (5047, "Inventario de mercancías"),
    "5135":   (5215, "Otros servicios"),
    "5145":   (5239, "Equipo computación"),
    "1524":   (5054, "Equipo de oficina"),
    "5195":   (5242, "Otros gastos generales"),
    "5120":   (5205, "Arrendamiento de Oficinas"),
    "1305":   (5008, "Cuentas por cobrar clientes nacionales"),
    "4135":   (5150, "Ventas"),
    "240801": (5100, "Impuesto a las ventas por pagar"),
    "135515": (5036, "Retención en la fuente a favor"),
}


def sembrar(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    Mapeo = apps.get_model("causacion", "MapeoCuentaAlegra")
    empresa = Empresa.objects.filter(nit="901234567").first()
    if empresa is None:
        return
    for puc, (id_alegra, nombre) in MAPEO.items():
        Mapeo.objects.get_or_create(
            empresa=empresa, cuenta_puc=puc,
            defaults={"id_alegra": id_alegra, "nombre_alegra": nombre},
        )


def deshacer(apps, schema_editor):
    pass  # los mapeos son editables por el usuario: no se borran al revertir


class Migration(migrations.Migration):
    dependencies = [
        ("causacion", "0008_facturacompra_factura_original_facturacompra_tipo"),
        ("core", "0002_empresa_beta_cero"),
    ]
    operations = [migrations.RunPython(sembrar, deshacer)]
