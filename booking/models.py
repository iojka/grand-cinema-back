"""M2 Réservation et stock de places (EPIC 2 et 7)

États d'une place pour une séance (règle métier du B1) :
- libre : aucune ligne Ticket pour le couple (séance, place) ;
- bloquée : une ligne Ticket au statut HELD, la réservation expire
  10 minutes après ;
- vendue : la ligne Ticket passe au statut SOLD (paiement Stripe
  confirmé ou vente au guichet).
La contrainte d'unicité (séance, place) empêche toute double vente,
en ligne comme au guichet
"""

import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from programme.models import Price, Screening, Seat

# US 2.2 : durée du blocage des places en attente de paiement
HOLD_DURATION = timedelta(minutes=10)

# Sans 0/O ni 1/I pour éviter les erreurs de lecture au guichet
# (recherche par référence en mode dégradé, US 7.3)
REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_reference() -> str:
    """Génère la référence courte communiquée au spectateur

    Le module secrets produit une valeur non prévisible.

    :return: une chaîne de 8 caractères de REFERENCE_ALPHABET
    """
    return "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))


class Booking(models.Model):
    """Réservation d'une ou plusieurs places pour une séance"""

    class Channel(models.TextChoices):
        WEB = "WEB", "En ligne"
        BOX_OFFICE = "BOX_OFFICE", "Guichet"

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente de paiement"
        CONFIRMED = "CONFIRMED", "Confirmée"
        EXPIRED = "EXPIRED", "Expirée"
        CANCELLED = "CANCELLED", "Annulée"

    class PaymentMethod(models.TextChoices):
        ONLINE_CARD = "ONLINE_CARD", "Carte en ligne (Stripe)"
        CASH = "CASH", "Espèces"
        CARD_TERMINAL = "CARD_TERMINAL", "Carte (terminal du guichet)"

    # UUID : identifiant non prévisible qui ne révèle pas le volume
    # des ventes (cours BDR, gestion des utilisateurs)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(
        "référence",
        max_length=8,
        unique=True,
        default=generate_reference,
        editable=False,
    )
    # PROTECT : une séance qui a des réservations ne peut pas être
    # supprimée, elle doit être annulée (US 6.1)
    screening = models.ForeignKey(
        Screening,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name="séance",
    )
    channel = models.CharField("canal", max_length=10, choices=Channel.choices)
    status = models.CharField(
        "statut",
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # Coordonnées du spectateur sans compte (US 2.4), facultatives
    # au guichet
    customer_name = models.CharField("nom", max_length=100, blank=True)
    customer_email = models.EmailField("adresse e-mail", blank=True)
    customer_postcode = models.CharField(
        "code postal", max_length=10, blank=True
    )
    customer_country = models.CharField(
        "pays (code ISO)", max_length=2, blank=True
    )
    total_amount = models.DecimalField(
        "montant total (€)", max_digits=7, decimal_places=2, default=0
    )
    payment_method = models.CharField(
        "mode de paiement",
        max_length=15,
        choices=PaymentMethod.choices,
        blank=True,
    )
    # Aucune donnée de carte : seul l'identifiant de la session de
    # paiement Stripe est conservé (US 3.1).
    # null=True volontaire : les ventes au guichet n'ont pas de session
    # (NULL) ; plusieurs chaînes vides seraient refusées par l'unicité.
    stripe_session_id = models.CharField(  # noqa: DJ001
        "session de paiement Stripe",
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField(
        "expiration du blocage", null=True, blank=True
    )
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    confirmed_at = models.DateTimeField("confirmée le", null=True, blank=True)
    # Agent d'accueil qui a vendu au guichet (vide en ligne, US 7.2)
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        verbose_name="vendu par",
    )

    class Meta:
        db_table = "bookings"
        verbose_name = "réservation"
        ordering = ["-created_at"]
        indexes = [
            # Tâche planifiée : recherche des réservations en attente
            # dont le blocage a expiré
            models.Index(
                fields=["status", "expires_at"],
                name="booking_status_expiry_idx",
            ),
        ]
        constraints = [
            # Une réservation en ligne doit avoir une adresse e-mail
            # pour l'envoi du billet (US 4.2)
            models.CheckConstraint(
                condition=models.Q(channel="BOX_OFFICE")
                | ~models.Q(customer_email=""),
                name="web_booking_requires_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reference} - {self.screening}"


class Ticket(models.Model):
    """Place réservée pour une séance : une ligne = un billet (QR code)"""

    class Status(models.TextChoices):
        HELD = "HELD", "Bloquée"
        SOLD = "SOLD", "Vendue"

    # UUID : identifiant signé contenu dans le QR code, sans donnée
    # personnelle (US 4.1)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="tickets",
        verbose_name="réservation",
    )
    # La séance est aussi portée par le billet pour que PostgreSQL
    # garantisse lui-même l'unicité (séance, place)
    screening = models.ForeignKey(
        Screening,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="séance",
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="place",
    )
    price = models.ForeignKey(
        Price,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="tarif",
    )
    # Prix figé au moment de la vente (tarif + supplément de salle) :
    # un changement de tarif ne modifie pas les réservations déjà
    # payées (US 6.2)
    unit_price = models.DecimalField(
        "prix payé (€)", max_digits=6, decimal_places=2
    )
    status = models.CharField(
        "statut", max_length=4, choices=Status.choices, default=Status.HELD
    )
    # Heure du 1er passage, affichée si le billet est rescanné (US 7.3)
    scanned_at = models.DateTimeField("scanné le", null=True, blank=True)
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scanned_tickets",
        verbose_name="scanné par",
    )

    class Meta:
        db_table = "tickets"
        verbose_name = "billet"
        ordering = ["seat__row", "seat__number"]
        constraints = [
            # Stock unique de places (US 2.2 et 7.2) : une place n'est
            # prise qu'une seule fois par séance
            models.UniqueConstraint(
                fields=["screening", "seat"],
                name="unique_seat_per_screening",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.seat} - {self.get_status_display()}"

    def clean(self) -> None:
        """Vérifie la cohérence du billet avec sa réservation

        :raises ValidationError: si la séance n'est pas celle de la
            réservation ou si la place n'est pas dans la bonne salle
        """
        super().clean()
        if (
            self.booking_id
            and self.screening_id
            and self.booking.screening_id != self.screening_id
        ):
            raise ValidationError(
                {"screening": "Le billet doit concerner la séance réservée."}
            )
        if (
            self.seat_id
            and self.screening_id
            and self.seat.room_id != self.screening.room_id
        ):
            raise ValidationError(
                {"seat": "La place doit appartenir à la salle de la séance."}
            )
