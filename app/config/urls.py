from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("causacion/", include("causacion.urls")),
    path("bancos/", include("conciliacion.urls")),
    path("calendario/", include("calendario.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    # Soportes (fotos) en desarrollo; en producción los servirá el proxy.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
