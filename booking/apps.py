"""Configuration de l'application booking (module M2 du B1)"""

from django.apps import AppConfig


class BookingConfig(AppConfig):
    """Déclaration de l'application auprès de Django"""

    name = "booking"
    verbose_name = "M2 - Réservation et stock de places"
