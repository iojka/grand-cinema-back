"""M3 Paiement (EPIC 3) : journal des notifications Stripe reçues

Contrôle anti-doublon (B1) : Stripe peut envoyer plusieurs fois la même
notification. L'identifiant de l'événement est unique en base : un même
événement n'est donc traité qu'une seule fois
"""

from django.db import models

from booking.models import Booking


class StripeEvent(models.Model):
    """Notification de paiement reçue de Stripe (webhook signé)"""

    event_id = models.CharField(
        "identifiant de l'événement Stripe", max_length=255, unique=True
    )
    event_type = models.CharField("type d'événement", max_length=100)
    received_at = models.DateTimeField("reçu le", auto_now_add=True)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stripe_events",
        verbose_name="réservation",
    )

    class Meta:
        db_table = "stripe_events"
        verbose_name = "événement Stripe"
        verbose_name_plural = "événements Stripe"
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.event_id})"
