"""M5 Pilotage (EPIC 8)

Les tableaux de bord sont calculés à partir des séances (M1) et des
billets vendus (M2) ; seules les alertes de remplissage ont leurs
tables (US 8.3)
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from programme.models import Screening

# Seuil utilisé tant qu'Isabelle n'a rien réglé (US 8.3, critère 1)
DEFAULT_THRESHOLD = 80


class AlertSetting(models.Model):
    """Réglage des alertes de remplissage, modifiable par Isabelle"""

    threshold = models.PositiveSmallIntegerField(
        "seuil d'alerte (%)",
        default=DEFAULT_THRESHOLD,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )

    class Meta:
        db_table = "alert_settings"
        verbose_name = "réglage des alertes"
        verbose_name_plural = "réglage des alertes"

    def __str__(self) -> str:
        return f"Seuil d'alerte : {self.threshold} %"


class OccupancyAlert(models.Model):
    """Alerte envoyée quand une séance franchit le seuil (US 8.3)

    Une seule alerte par séance : OneToOneField crée une contrainte
    d'unicité, la base refuse donc une 2e alerte (critère 2)
    """

    screening = models.OneToOneField(
        Screening,
        on_delete=models.CASCADE,
        related_name="occupancy_alert",
        verbose_name="séance",
    )
    fill_rate = models.PositiveSmallIntegerField("taux lors de l'alerte (%)")
    sent_at = models.DateTimeField("envoyée le", auto_now_add=True)

    class Meta:
        db_table = "occupancy_alerts"
        verbose_name = "alerte de remplissage"
        verbose_name_plural = "alertes de remplissage"
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"{self.screening} : {self.fill_rate} %"
