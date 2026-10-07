"""M1 Programme et séances : films, salles, places, tarifs et séances

Couvre les EPIC 1 (consulter le programme) et 6 (gérer la programmation)
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

# US 6.1 : marge entre deux séances d'une même salle (sortie, nettoyage)
CLEANING_MARGIN = timedelta(minutes=15)


class Movie(models.Model):
    """Film à l'affiche, avec les informations de la fiche film (US 1.3)"""

    class Rating(models.TextChoices):
        ALL = "TP", "Tous publics"
        UNDER_12 = "-12", "Interdit aux moins de 12 ans"
        UNDER_16 = "-16", "Interdit aux moins de 16 ans"
        UNDER_18 = "-18", "Interdit aux moins de 18 ans"

    class Version(models.TextChoices):
        VF = "VF", "Version française"
        VOST = "VOST", "Version originale sous-titrée"

    title = models.CharField("titre", max_length=200)
    synopsis = models.TextField("synopsis")
    duration_minutes = models.PositiveSmallIntegerField(
        "durée (minutes)", validators=[MinValueValidator(1)]
    )
    poster = models.ImageField("affiche", upload_to="posters/", blank=True)
    rating = models.CharField(
        "classification",
        max_length=3,
        choices=Rating.choices,
        default=Rating.ALL,
    )
    version = models.CharField(
        "version", max_length=4, choices=Version.choices
    )
    # Filtre « jeune public » du programme (US 1.2)
    is_young_audience = models.BooleanField("jeune public", default=False)

    class Meta:
        db_table = "movies"
        verbose_name = "film"
        ordering = ["title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.version})"


class Room(models.Model):
    """Salle du cinéma ; le supplément s'ajoute au tarif (US 2.3, 6.2)"""

    class Category(models.TextChoices):
        PREMIUM = "PREMIUM", "Premium / IMAX"
        STANDARD = "STANDARD", "Standard"
        VIP = "VIP", "VIP"
        EVENT = "EVENT", "Événementielle"

    name = models.CharField("nom", max_length=50, unique=True)
    category = models.CharField(
        "catégorie", max_length=10, choices=Category.choices
    )
    supplement = models.DecimalField(
        "supplément (€)",
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        db_table = "rooms"
        verbose_name = "salle"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def capacity(self) -> int:
        """Calcule la capacité de la salle

        :return: le nombre de places actives du plan de salle
        """
        return self.seats.filter(is_active=True).count()


class Seat(models.Model):
    """Place physique d'une salle

    Deux places sont côte à côte si elles sont dans la même rangée avec
    des numéros qui se suivent (US 2.2)
    """

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="seats",
        verbose_name="salle",
    )
    row = models.CharField("rangée", max_length=2)
    number = models.PositiveSmallIntegerField("numéro")
    is_accessible = models.BooleanField("place PMR", default=False)
    # Une place retirée du plan est désactivée, pas supprimée :
    # les billets déjà vendus pour cette place restent cohérents
    is_active = models.BooleanField("active", default=True)

    class Meta:
        db_table = "seats"
        verbose_name = "place"
        ordering = ["room", "row", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "row", "number"],
                name="unique_seat_position",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.room} - {self.row}{self.number}"


class Price(models.Model):
    """Tarif de base (plein, réduit, enfant), paramétré par Isabelle"""

    label = models.CharField("libellé", max_length=50, unique=True)
    # DECIMAL : seul type qui garantit des calculs exacts sur les prix
    amount = models.DecimalField(
        "prix (€)",
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    requires_proof = models.BooleanField(
        "justificatif demandé à l'entrée", default=False
    )
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        db_table = "prices"
        verbose_name = "tarif"
        ordering = ["-amount"]

    def __str__(self) -> str:
        return f"{self.label} ({self.amount} €)"

    def amount_for(self, room: Room) -> Decimal:
        """Calcule le prix d'une place : tarif + supplément de la salle

        Le prix calculé est recopié dans le billet (Ticket.unit_price) :
        une modification du tarif ne change pas les billets déjà payés
        (US 6.2)

        :param room: salle de la séance (supplément IMAX / VIP)
        :return: le prix de la place en euros
        """
        return self.amount + room.supplement


class Screening(models.Model):
    """Séance : un film projeté dans une salle à une date et une heure"""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Programmée"
        CANCELLED = "CANCELLED", "Annulée"

    # PROTECT : un film ou une salle utilisés par une séance
    # ne peuvent pas être supprimés
    movie = models.ForeignKey(
        Movie,
        on_delete=models.PROTECT,
        related_name="screenings",
        verbose_name="film",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="screenings",
        verbose_name="salle",
    )
    # Index : le programme des 7 jours filtre sur cette colonne (US 1.1)
    starts_at = models.DateTimeField("début", db_index=True)
    status = models.CharField(
        "statut",
        max_length=10,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )

    class Meta:
        db_table = "screenings"
        verbose_name = "séance"
        ordering = ["starts_at"]

    def __str__(self) -> str:
        start = f"{self.starts_at:%d/%m/%Y %H:%M}"
        return f"{self.movie.title} - {self.room} - {start}"

    @property
    def ends_at(self) -> datetime:
        """Calcule l'heure de fin de la séance

        :return: l'heure de début augmentée de la durée du film
        """
        return self.starts_at + timedelta(minutes=self.movie.duration_minutes)

    def clean(self) -> None:
        """Refuse une séance qui en chevauche une autre (US 6.1)

        Deux séances d'une même salle doivent être séparées par la durée
        du film et 15 minutes de marge.

        :raises ValidationError: si la séance chevauche une autre séance
        """
        super().clean()
        if not (self.starts_at and self.movie_id and self.room_id):
            return
        if self.status == self.Status.CANCELLED:
            return
        start = self.starts_at
        end = self.ends_at + CLEANING_MARGIN
        candidates = (
            Screening.objects.filter(
                room_id=self.room_id,
                status=self.Status.SCHEDULED,
                starts_at__lt=end,
                starts_at__gt=start - timedelta(days=1),
            )
            .exclude(pk=self.pk)
            .select_related("movie")
        )
        for other in candidates:
            if other.ends_at + CLEANING_MARGIN > start:
                raise ValidationError(
                    f"Cette séance chevauche « {other} » "
                    "(durée du film + 15 minutes de marge)."
                )
