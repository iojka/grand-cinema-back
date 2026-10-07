"""Tests de l'API du programme de la semaine (US 1.1)"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from booking.models import Ticket
from programme.models import Screening

pytestmark = pytest.mark.django_db

URL = "/api/programme/"


def at(days, hour):
    """Calcule une date dans quelques jours, à l'heure donnée

    :param days: nombre de jours à partir d'aujourd'hui (négatif = passé)
    :param hour: heure de la séance
    :return: la date et l'heure (heure de Paris)
    """
    day = timezone.localtime() + timedelta(days=days)
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


def sell(make_booking, screening, seats, price):
    """Vend une place pour chaque place de la liste"""
    booking = make_booking()
    for seat in seats:
        Ticket.objects.create(
            booking=booking,
            screening=screening,
            seat=seat,
            price=price,
            unit_price=Decimal("11.00"),
        )


def test_programme_is_public(client):
    """Le spectateur consulte le programme sans compte"""
    response = client.get(URL)

    assert response.status_code == 200


def test_programme_shows_next_7_days_sorted(client, movie, room):
    """Critère 1 : séances des 7 prochains jours, triées par jour et heure"""
    later = Screening.objects.create(
        movie=movie, room=room, starts_at=at(2, 20)
    )
    first = Screening.objects.create(
        movie=movie, room=room, starts_at=at(1, 14)
    )
    second = Screening.objects.create(
        movie=movie, room=room, starts_at=at(1, 20)
    )
    # Hors programme : dans plus de 7 jours, ou déjà passée
    Screening.objects.create(movie=movie, room=room, starts_at=at(9, 20))
    Screening.objects.create(movie=movie, room=room, starts_at=at(-1, 20))

    response = client.get(URL)

    ids = [item["id"] for item in response.json()]
    assert ids == [first.pk, second.pk, later.pk]


def test_screening_shows_movie_time_room_and_remaining_seats(
    client, make_booking, screening, seats, price
):
    """Critère 2 : film, heure, salle et nombre de places restantes"""
    sell(make_booking, screening, seats[:1], price)

    item = client.get(URL).json()[0]

    assert item["movie"]["title"] == "Film test"
    assert item["starts_at"] is not None
    assert item["room"] == "Salle test"
    assert item["remaining_seats"] == 3
    assert item["is_full"] is False


def test_full_screening_is_marked_full(
    client, make_booking, screening, seats, price
):
    """Critère 3 : une séance complète est signalée"""
    sell(make_booking, screening, seats, price)

    item = client.get(URL).json()[0]

    assert item["remaining_seats"] == 0
    assert item["is_full"] is True


def test_change_by_isabelle_is_visible_on_refresh(client, screening):
    """Critère 4 : une séance annulée disparaît au rechargement"""
    assert len(client.get(URL).json()) == 1

    screening.status = Screening.Status.CANCELLED
    screening.save()

    assert client.get(URL).json() == []
