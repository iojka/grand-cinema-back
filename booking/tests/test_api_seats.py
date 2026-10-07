"""Tests de l'API du plan de salle d'une séance (US 2.1)"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from booking.models import Ticket
from programme.models import Screening

pytestmark = pytest.mark.django_db


def url(screening_id):
    """Adresse du plan de salle d'une séance"""
    return f"/api/booking/screenings/{screening_id}/seats/"


def take(make_booking, screening, seat, price, status):
    """Crée un billet bloqué (HELD) ou vendu (SOLD) pour une place"""
    Ticket.objects.create(
        booking=make_booking(),
        screening=screening,
        seat=seat,
        price=price,
        unit_price=Decimal("11.00"),
        status=status,
    )


def test_seat_map_is_public_and_shows_free_seats(client, screening, seats):
    """Le spectateur voit le plan de salle sans compte"""
    response = client.get(url(screening.pk))

    assert response.status_code == 200
    data = response.json()
    assert data["movie"]["title"] == "Film test"
    assert data["room"] == "Salle test"
    assert [seat["status"] for seat in data["seats"]] == ["FREE"] * 4


def test_seat_map_shows_held_and_sold_seats(
    client, make_booking, screening, seats, price
):
    """Critères 1 et 2 : places libres, bloquées et vendues"""
    take(make_booking, screening, seats[0], price, Ticket.Status.HELD)
    take(make_booking, screening, seats[1], price, Ticket.Status.SOLD)

    data = client.get(url(screening.pk)).json()

    statuses = {seat["number"]: seat["status"] for seat in data["seats"]}
    assert statuses == {1: "HELD", 2: "SOLD", 3: "FREE", 4: "FREE"}
    assert data["remaining_seats"] == 2


def test_inactive_seat_is_not_in_the_seat_map(client, screening, seats):
    """Une place retirée du plan (US 6.2) n'est pas affichée"""
    seats[0].is_active = False
    seats[0].save()

    data = client.get(url(screening.pk)).json()

    assert len(data["seats"]) == 3


def test_full_screening_is_marked_full(
    client, make_booking, screening, seats, price
):
    """Critère 3 : une séance complète est signalée"""
    for seat in seats:
        take(make_booking, screening, seat, price, Ticket.Status.SOLD)

    data = client.get(url(screening.pk)).json()

    assert data["is_full"] is True


def test_past_or_cancelled_screening_returns_404(client, screening, seats):
    """Une séance passée ou annulée n'est plus réservable"""
    past = Screening.objects.create(
        movie=screening.movie,
        room=screening.room,
        starts_at=timezone.now() - timedelta(days=2),
    )
    screening.status = Screening.Status.CANCELLED
    screening.save()

    assert client.get(url(past.pk)).status_code == 404
    assert client.get(url(screening.pk)).status_code == 404
