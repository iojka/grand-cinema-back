"""Tests du blocage des places côte à côte (US 2.2)"""

import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.utils import timezone

from booking.models import Booking, Ticket

HOLDS_URL = "/api/booking/holds/"


def hold(client, screening, seats):
    """Demande le blocage d'une liste de places pour une séance"""
    return client.post(
        HOLDS_URL,
        {"screening": screening.pk, "seats": [seat.pk for seat in seats]},
        content_type="application/json",
    )


@pytest.mark.django_db
def test_adjacent_seats_are_held_for_10_minutes(
    client, screening, seats, price
):
    """Critère 1 : places côte à côte bloquées 10 minutes"""
    response = hold(client, screening, seats[:3])

    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.json()["id"])
    assert booking.status == Booking.Status.PENDING
    assert booking.tickets.filter(status=Ticket.Status.HELD).count() == 3
    remaining = booking.expires_at - timezone.now()
    assert timedelta(minutes=9) < remaining <= timedelta(minutes=10)
    assert response.json()["total_amount"] == "33.00"


@pytest.mark.django_db
def test_seats_must_be_side_by_side(client, screening, seats, price):
    """Critère 1 : A1 et A3 ne sont pas côte à côte, refus"""
    response = hold(client, screening, [seats[0], seats[2]])

    assert response.status_code == 400
    assert Ticket.objects.count() == 0


@pytest.mark.django_db
def test_at_least_one_seat_is_needed(client, screening, seats, price):
    """Une demande sans place est refusée"""
    response = hold(client, screening, [])

    assert response.status_code == 400


@pytest.mark.django_db
def test_taken_seat_is_refused_with_a_message(
    client, make_booking, screening, seats, price
):
    """Critère 2 : place déjà prise, message et aucun blocage partiel"""
    Ticket.objects.create(
        booking=make_booking(),
        screening=screening,
        seat=seats[1],
        price=price,
        unit_price=Decimal("11.00"),
    )

    response = hold(client, screening, seats[:2])

    assert response.status_code == 409
    assert "detail" in response.json()
    # A1 n'a pas été bloquée : tout ou rien
    assert Ticket.objects.count() == 1


@pytest.mark.django_db
def test_expired_hold_is_released(
    client, make_booking, screening, seats, price
):
    """Critère 3 : après 10 minutes sans paiement, la place est libérée"""
    expired = make_booking(expires_at=timezone.now() - timedelta(minutes=1))
    Ticket.objects.create(
        booking=expired,
        screening=screening,
        seat=seats[0],
        price=price,
        unit_price=Decimal("11.00"),
    )

    data = client.get(f"/api/booking/screenings/{screening.pk}/seats/").json()

    assert data["seats"][0]["status"] == "FREE"
    expired.refresh_from_db()
    assert expired.status == Booking.Status.EXPIRED


@pytest.mark.django_db(transaction=True)
def test_only_one_of_two_simultaneous_holds_succeeds(screening, seats, price):
    """Critère 4 : test de concurrence, deux spectateurs, une même place"""
    results = []
    start = threading.Barrier(2)  # les deux demandes partent ensemble

    def spectator():
        start.wait()
        response = hold(Client(), screening, [seats[0]])
        results.append(response.status_code)
        connection.close()  # chaque thread ferme sa connexion à la base

    threads = [threading.Thread(target=spectator) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [201, 409]
    assert Ticket.objects.filter(seat=seats[0]).count() == 1
