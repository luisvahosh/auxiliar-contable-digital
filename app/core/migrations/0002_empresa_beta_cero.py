# Semilla de la empresa beta cero (PROCESO-AUXILIAR-CONTABLE.md: la propia
# empresa de Luis). El NIT coincide con el adquiriente de los XML de
# datos-prueba/. Cuando exista el onboarding real de tenants, esta empresa
# se edita o reemplaza desde el admin.
from django.db import migrations


def crear_empresa(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    Empresa.objects.get_or_create(nit="901234567",
                                  defaults={"razon_social": "LEARNWAY SAS"})


def eliminar_empresa(apps, schema_editor):
    Empresa = apps.get_model("core", "Empresa")
    Empresa.objects.filter(nit="901234567").delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(crear_empresa, eliminar_empresa)]
