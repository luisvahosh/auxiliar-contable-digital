"""
Genera los embeddings de las fichas del corpus que aún no los tienen, para
habilitar la búsqueda semántica. Sin NVIDIA_API_KEY, el asistente igual
funciona por coincidencia de términos.
  python manage.py indexar_corpus [--todos]
"""
from django.core.management.base import BaseCommand

from asistente.embeddings import embed, esta_configurado
from asistente.models import ArticuloNormativo


class Command(BaseCommand):
    help = "Genera los embeddings del corpus normativo."

    def add_arguments(self, parser):
        parser.add_argument("--todos", action="store_true",
                            help="Reindexa también los que ya tienen embedding")

    def handle(self, *args, **opciones):
        if not esta_configurado():
            self.stdout.write(self.style.WARNING(
                "NVIDIA_API_KEY no configurada: el asistente funcionará por "
                "coincidencia de términos, sin búsqueda semántica."))
            return
        qs = ArticuloNormativo.objects.all()
        if not opciones["todos"]:
            qs = qs.filter(embedding__isnull=True)
        hechos = fallidos = 0
        for articulo in qs:
            vector = embed(articulo.titulo + ". " + articulo.texto, tipo="passage")
            if vector:
                articulo.embedding = vector
                articulo.save(update_fields=["embedding"])
                hechos += 1
            else:
                fallidos += 1
        self.stdout.write(f"Indexados {hechos}; fallidos {fallidos}.")
