# Re-guarda las conexiones existentes para que sus tokens (que estaban en
# claro) queden cifrados en reposo. Leer un valor en claro es seguro: el
# descifrador devuelve el valor tal cual si no es un cifrado válido, y el
# save() lo escribe ya cifrado.
from django.db import migrations


def cifrar_existentes(apps, schema_editor):
    Conexion = apps.get_model("causacion", "ConexionContable")
    for conexion in Conexion.objects.all():
        conexion.save(update_fields=["token"])


class Migration(migrations.Migration):
    dependencies = [("causacion", "0011_alter_conexioncontable_token")]
    operations = [migrations.RunPython(cifrar_existentes, migrations.RunPython.noop)]
