"""Tests du tableau de bord du remplissage (US 8.1)"""

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from booking.models import Booking, Ticket
from booking.services import hold_seats, sell_at_box_office
from programme.models import Screening

pytestmark = pytest.mark.django_db

URL = "/api/dashboard/occupancy/"

# Période de test fixe : lundi 7 au lundi 14 janvier 2030
PERIOD = {"start": "2030-01-07", "end": "2030-01-14"}


@pytest.fixture
def manager_client(client, make_user):
    """Client connecté avec le compte d'Isabelle (administratrice)"""
    client.force_login(make_user(User.Role.ADMIN))
    return client


@pytest.fixture
def january(movie, room, seats, price, make_user):
    """Trois séances de janvier 2030 dans la salle de test (4 places)

    Lundi 7 : 2 places web et 1 au guichet ; mardi 8 : 1 place web ;
    lundi 14 (semaine suivante) : aucune place vendue
    """
    agent = make_user(User.Role.BOX_OFFICE)
    monday = make_screening(movie, room, 7)
    tuesday = make_screening(movie, room, 8)
    next_monday = make_screening(movie, room, 14)
    pay_online(monday, seats[:2])
    tickets = [{"seat": seats[2], "price": price}]
    sell_at_box_office(monday, tickets, Booking.PaymentMethod.CASH, agent)
    hold_seats(monday, seats[3:4])  # bloquée : pas encore vendue
    pay_online(tuesday, seats[:1])
    return [monday, tuesday, next_monday]


def make_screening(movie, room, day):
    """Séance de janvier 2030 à 20 h (heure de Paris)"""
    starts_at = timezone.make_aware(datetime(2030, 1, day, 20, 0))
    return Screening.objects.create(
        movie=movie, room=room, starts_at=starts_at
    )


def pay_online(screening, seats):
    """Réservation en ligne payée : billets vendus"""
    booking = hold_seats(screening, seats)
    booking.customer_email = "marine@example.com"
    booking.status = Booking.Status.CONFIRMED
    booking.save()
    booking.tickets.update(status=Ticket.Status.SOLD)


def test_fill_rate_by_screening(manager_client, january):
    """Critère 1 : taux par séance (places vendues / capacité)"""
    response = manager_client.get(URL, PERIOD)

    assert response.status_code == 200
    rates = [item["fill_rate"] for item in response.json()["screenings"]]
    assert rates == [75, 25, 0]


def test_fill_rate_by_room_day_and_week(manager_client, january):
    """Critère 1 : taux par salle, par jour et par semaine"""
    data = manager_client.get(URL, PERIOD).json()

    assert data["rooms"] == [
        {"label": "Salle test", "capacity": 12, "sold": 4, "fill_rate": 33}
    ]
    assert [(day["label"], day["fill_rate"]) for day in data["days"]] == [
        ("2030-01-07", 75),
        ("2030-01-08", 25),
        ("2030-01-14", 0),
    ]
    # Semaine désignée par son lundi
    assert [(week["label"], week["fill_rate"]) for week in data["weeks"]] == [
        ("2030-01-07", 50),
        ("2030-01-14", 0),
    ]


def test_compare_web_and_box_office_sales(manager_client, january):
    """Critère 3 : ventes web et guichet de la période"""
    data = manager_client.get(URL, PERIOD).json()

    assert data["web"] == 3
    assert data["box_office"] == 1


def test_choose_a_period(manager_client, january):
    """Critère 3 : seules les séances de la période choisie comptent"""
    period = {"start": "2030-01-08", "end": "2030-01-08"}

    data = manager_client.get(URL, period).json()

    assert [item["id"] for item in data["screenings"]] == [january[1].pk]
    assert data["web"] == 1
    assert data["box_office"] == 0


def test_cancelled_screening_is_ignored(manager_client, january):
    """Une séance annulée ne fausse pas les taux"""
    january[2].status = Screening.Status.CANCELLED
    january[2].save()

    data = manager_client.get(URL, PERIOD).json()

    assert len(data["screenings"]) == 2


def test_default_period_is_the_last_7_days(manager_client, movie, room):
    """Sans période choisie : les 7 derniers jours, aujourd'hui compris"""
    now = timezone.localtime()
    today = now.replace(hour=10, minute=0, second=0, microsecond=0)
    recent = Screening.objects.create(
        movie=movie, room=room, starts_at=today - timedelta(days=6)
    )
    Screening.objects.create(  # trop ancienne
        movie=movie, room=room, starts_at=today - timedelta(days=7)
    )

    data = manager_client.get(URL).json()

    assert [item["id"] for item in data["screenings"]] == [recent.pk]


def test_invalid_period_is_refused(manager_client):
    """Date mal écrite ou début après la fin : demande refusée"""
    bad_date = {"start": "lundi", "end": "2030-01-14"}
    reversed_period = {"start": "2030-01-14", "end": "2030-01-07"}

    assert manager_client.get(URL, bad_date).status_code == 400
    assert manager_client.get(URL, reversed_period).status_code == 400


def test_only_isabelle_and_management_see_the_dashboard(client, make_user):
    """Tableau de bord réservé à Isabelle et à la direction (US 9.1)"""
    assert client.get(URL).status_code == 401
    client.force_login(make_user(User.Role.BOX_OFFICE))
    assert client.get(URL).status_code == 403
    client.force_login(make_user(User.Role.MANAGEMENT))
    assert client.get(URL).status_code == 200
