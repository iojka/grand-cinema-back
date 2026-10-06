"""Configuration de l'application programme (module M1 du B1)."""

from django.apps import AppConfig


class ProgrammeConfig(AppConfig):
    """Déclaration de l'application auprès de Django."""

    name = "programme"
    verbose_name = "M1 - Programme et séances"
