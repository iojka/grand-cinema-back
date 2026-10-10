"""M5 Pilotage (EPIC 8)

Les tableaux de bord et les indicateurs sont calculés à partir des
séances (M1) et des billets vendus (M2) ; seuls les réglages d'Isabelle
et les alertes de remplissage ont leurs tables (US 8.2 et 8.3)
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from programme.models import Screening

# Seuil utilisé tant qu'Isabelle n'a rien réglé (US 8.3, critère 1)
DEFAULT_THRESHOLD = 80
# Date de lancement utilisée tant qu'Isabelle n'a rien réglé (US 8.2)
DEFAULT_LAUNCH_DATE = date(2026, 10, 1)


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


class KpiSetting(models.Model):
    """Réglage des indicateurs du projet, modifiable par Isabelle (US 8.2)

    La date de lancement est le point de départ des cumuls ; les dates
    du festival servent au remplissage en affluence et aux touristes
    """

    launch_date = models.DateField(
        "date de lancement", default=DEFAULT_LAUNCH_DATE
    )
    festival_start = models.DateField(
        "début du festival", null=True, blank=True
    )
    festival_end = models.DateField("fin du festival", null=True, blank=True)

    class Meta:
        db_table = "kpi_settings"
        verbose_name = "réglage des indicateurs"
        verbose_name_plural = "réglage des indicateurs"

    def __str__(self) -> str:
        return f"Lancement le {self.launch_date:%d/%m/%Y}"

    def clean(self):
        """Vérifie que le festival ne finit pas avant de commencer"""
        if (
            self.festival_start
            and self.festival_end
            and self.festival_end < self.festival_start
        ):
            raise ValidationError(
                {"festival_end": "La fin du festival doit suivre son début."}
            )
