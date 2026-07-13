from django.db import models


class ArticuloNormativo(models.Model):
    """Una ficha del corpus normativo (global, no por empresa: el Estatuto
    Tributario es el mismo para todas). El embedding se genera con
    `indexar_corpus`; la búsqueda cae a coincidencia de términos si falta."""

    tema = models.SlugField(unique=True)
    titulo = models.CharField(max_length=200)
    referencia = models.CharField("referencia normativa", max_length=120,
                                  help_text="Ej.: art. 392 E.T.")
    texto = models.TextField()
    fuente_url = models.URLField(blank=True)
    embedding = models.JSONField(null=True, blank=True, editable=False)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "artículo normativo"
        verbose_name_plural = "corpus normativo"

    def __str__(self):
        return f"{self.titulo} ({self.referencia})"
