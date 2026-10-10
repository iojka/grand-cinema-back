"""Configuration de l'application payment (module M3 du B1)"""

from django.apps import AppConfig


class PaymentConfig(AppConfig):
    """Déclaration de l'application auprès de Django"""

    name = "payment"
    verbose_name = "M3 - Paiement"
