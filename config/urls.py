"""Routes URL du projet.

Toutes les routes de l'API sont préfixées par /api/. Les routes métier
seront ajoutées module par module (une US par branche).
"""

from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import health

admin.site.site_header = "Le Grand Cinéma - back office"
admin.site.site_title = "Le Grand Cinéma"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    # Documentation OpenAPI : schéma brut et interface Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
