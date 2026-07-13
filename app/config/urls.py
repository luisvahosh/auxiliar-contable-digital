from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as servir_archivo

urlpatterns = [
    path("admin/", admin.site.urls),
    path("causacion/", include("causacion.urls")),
    path("bancos/", include("conciliacion.urls")),
    path("calendario/", include("calendario.urls")),
    path("cierre/", include("cierre.urls")),
    path("nomina/", include("nomina.urls")),
    path("activos/", include("activos.urls")),
    path("", include("core.urls")),
    # Soportes (fotos): servidos por la app también en el contenedor beta.
    # Los nombres son UUID no adivinables; endurecer con auth cuando el
    # volumen lo pida (proxy dedicado o vista autenticada).
    re_path(r"^media/(?P<path>.*)$", servir_archivo,
            {"document_root": settings.MEDIA_ROOT}),
]
