"""Routes URL du projet.

Les routes de l'API seront ajoutées module par module (une US par
branche).
"""

from django.contrib import admin
from django.urls import path

admin.site.site_header = "Le Grand Cinéma - back office"
admin.site.site_title = "Le Grand Cinéma"

urlpatterns = [
    path("admin/", admin.site.urls),
]
