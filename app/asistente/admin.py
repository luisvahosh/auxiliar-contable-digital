from django.contrib import admin

from .models import ArticuloNormativo


@admin.register(ArticuloNormativo)
class ArticuloNormativoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "referencia", "actualizado")
    search_fields = ("titulo", "referencia", "texto")
    exclude = ("embedding",)  # se genera con indexar_corpus
