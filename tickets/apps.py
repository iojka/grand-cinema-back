"""Configuration de l'application tickets (module M4 du B1)"""

from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """Déclaration de l'application auprès de Django"""

    name = "tickets"
    verbose_name = "M4 - Billets et contrôle d'accès"
