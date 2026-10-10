"""Tests du suivi des réservations par séance (US 7.1)"""

import pytest
from django.utils import timezone

from accounts.models import User
from booking.models import Booking, Ticket
from booking.services import hold_seats, sell_at_box_office
from programme.models import Screening

pytestmark = pytest.mark.django_db

URL = "/api/booking/tracking/"


@pytest.fixture
def manager_client(client, make_user):
    """Client connecté avec le compte d'Isabelle (administratrice)"""
    client.force_login(make_user(User.Role.ADMIN))
    return client


def pay_online(screening, seats):
    """Réservation en ligne payée : billets vendus"""
    booking = hold_seats(screening, seats)
    booking.customer_email = "marine@example.com"
    booking.status = Booking.Status.CONFIRMED
    booking.save()
    booking.tickets.update(status=Ticket.Status.SOLD)
    return booking


def sell_one_seat(screening, seat, price, agent):
    """Vente d'une place au guichet, payée en espèces (US 7.2)"""
    tickets = [{"seat": seat, "price": price}]
    return sell_at_box_office(
        screening, tickets, Booking.PaymentMethod.CASH, agent
    )


def day_of(screening):
    """Jour de la séance à l'heure de Paris (format AAAA-MM-JJ)"""
    return timezone.localtime(screening.starts_at).date().isoformat()


def test_tracking_shows_sold_seats_capacity_rate_and_channels(
    manager_client, make_user, screening, seats, price
):
    """Critère 1 : vendues, capacité, taux et répartition web / guichet"""
    pay_online(screening, seats[:2])
    sell_one_seat(screening, seats[2], price, make_user(User.Role.BOX_OFFICE))
    hold_seats(screening, seats[3:4])  # bloquée : pas encore vendue

    response = manager_client.get(URL, {"date": day_of(screening)})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["movie"] == "Film test"
    assert data[0]["room"] == "Salle test"
    assert data[0]["capacity"] == 4
    assert data[0]["sold"] == 3
    assert data[0]["web"] == 2
    assert data[0]["box_office"] == 1
    assert data[0]["fill_rate"] == 75  # 3 places sur 4


def test_figures_are_recalculated_after_a_sale(
    manager_client, make_user, screening, seats, price
):
    """Critère 2 : une nouvelle lecture donne les chiffres à jour"""
    first = manager_client.get(URL, {"date": day_of(screening)})
    sell_one_seat(screening, seats[0], price, make_user(User.Role.BOX_OFFICE))

    second = manager_client.get(URL, {"date": day_of(screening)})

    assert first.json()[0]["sold"] == 0
    assert second.json()[0]["sold"] == 1


def test_screenings_of_the_day_by_default(
    manager_client, movie, room, screening
):
    """Critère 1 : sans date choisie, les séances du jour"""
    now = timezone.localtime()
    today = Screening.objects.create(
        movie=movie,
        room=room,
        starts_at=now.replace(hour=10, minute=0, second=0, microsecond=0),
    )

    response = manager_client.get(URL)

    assert [item["id"] for item in response.json()] == [today.pk]


def test_choose_a_date(manager_client, movie, room, screening):
    """Critère 3 : seules les séances de la date choisie s'affichent"""
    now = timezone.localtime()
    Screening.objects.create(
        movie=movie,
        room=room,
        starts_at=now.replace(hour=10, minute=0, second=0, microsecond=0),
    )

    response = manager_client.get(URL, {"date": day_of(screening)})

    assert [item["id"] for item in response.json()] == [screening.pk]


def test_cancelled_screening_is_hidden(manager_client, screening):
    """Une séance annulée n'est pas suivie"""
    screening.status = Screening.Status.CANCELLED
    screening.save()

    response = manager_client.get(URL, {"date": day_of(screening)})

    assert response.json() == []


def test_invalid_date_is_refused(manager_client):
    """Une date mal écrite est refusée"""
    response = manager_client.get(URL, {"date": "demain"})

    assert response.status_code == 400


def test_only_staff_can_follow_bookings(client, make_user, screening):
    """Suivi réservé à Isabelle, à la direction et à l'accueil (US 9.1)"""
    assert client.get(URL).status_code == 401
    client.force_login(make_user(User.Role.PROGRAMMING))
    assert client.get(URL).status_code == 403
    client.force_login(make_user(User.Role.MANAGEMENT))
    assert client.get(URL).status_code == 200
    client.force_login(make_user(User.Role.BOX_OFFICE))
    assert client.get(URL).status_code == 200
