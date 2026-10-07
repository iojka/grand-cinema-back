"""Point d'entrée ASGI

Non utilisé pour le MVP, conservé pour une évolution éventuelle
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
