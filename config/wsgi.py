"""Point d'entrée WSGI du serveur de production

Utilisé par le conteneur de l'API sur Azure Container Apps (H-02)
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
