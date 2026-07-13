"""
Agrega o reemplaza una ficha del corpus normativo desde un archivo de texto.
Útil para que el contador cargue el texto oficial de un artículo.
  python manage.py agregar_articulo <tema> <"Título"> <"ref"> <archivo.txt> [--url URL]
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from asistente.models import ArticuloNormativo


class Command(BaseCommand):
    help = "Agrega o reemplaza una ficha del corpus normativo."

    def add_arguments(self, parser):
        parser.add_argument("tema")
        parser.add_argument("titulo")
        parser.add_argument("referencia")
        parser.add_argument("archivo", help="Archivo .txt con el texto")
        parser.add_argument("--url", default="")

    def handle(self, *args, **o):
        ruta = Path(o["archivo"])
        if not ruta.is_file():
            raise CommandError(f"No existe el archivo {ruta}.")
        texto = ruta.read_text(encoding="utf-8").strip()
        articulo, creado = ArticuloNormativo.objects.update_or_create(
            tema=slugify(o["tema"]),
            defaults={"titulo": o["titulo"], "referencia": o["referencia"],
                      "texto": texto, "fuente_url": o["url"], "embedding": None})
        self.stdout.write(f"{'Creada' if creado else 'Actualizada'} la ficha "
                          f"«{articulo.titulo}». Corre indexar_corpus para la "
                          "búsqueda semántica.")
