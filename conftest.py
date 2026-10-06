"""Données de test partagées par tous les modules (fixtures pytest).

Chaque fixture prépare un objet en base de test ; pytest la fournit au
test qui la demande en paramètre.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from booking.models import Booking
from programme.models import Movie, Price, Room, Screening, Seat


@pytest.fixture
def room():
    """Salle standard sans supplément."""
    return Room.objects.create(
        name="Salle test",
        category=Room.Category.STANDARD,
        supplement=Decimal("0.00"),
    )


@pytest.fixture
def seats(room):
    """Quatre places côte à côte dans la rangée A de la salle de test."""
    return [
        Seat.objects.create(room=room, row="A", number=number)
        for number in range(1, 5)
    ]


@pytest.fixture
def movie():
    """Film de 2 heures en version française."""
    return Movie.objects.create(
        title="Film test",
        synopsis="Synopsis du film de test.",
        duration_minutes=120,
        version=Movie.Version.VF,
    )


@pytest.fixture
def price():
    """Plein tarif à 11 €."""
    return Price.objects.create(label="Plein tarif", amount=Decimal("11.00"))


@pytest.fixture
def screening(movie, room):
    """Séance de demain à 20 h dans la salle de test."""
    tomorrow = timezone.now() + timedelta(days=1)
    starts_at = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)
    return Screening.objects.create(
        movie=movie, room=room, starts_at=starts_at
    )


@pytest.fixture
def make_booking(screening):
    """Fabrique de réservations en ligne pour la séance de test.

    :return: une fonction qui crée une réservation ; ses paramètres
        nommés remplacent les valeurs par défaut
    """

    def _make_booking(**fields):
        values = {
            "screening": screening,
            "channel": Booking.Channel.WEB,
            "customer_name": "Jacky",
            "customer_email": "jacky@example.com",
            "customer_postcode": "48000",
        }
        values.update(fields)
        return Booking.objects.create(**values)

    return _make_booking
