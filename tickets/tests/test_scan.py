"""Tests du contrôle des billets à l'entrée (US 7.3)"""

import time
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from booking.services import hold_seats
from programme.models import Screening
from tickets.services import ticket_token

pytestmark = pytest.mark.django_db

URL = "/api/tickets/scan/"


def scan(client, screening, code):
    """Scan d'un QR code pour la séance contrôlée par l'agent"""
    data = {"screening": screening.pk, "code": code}
    return client.post(URL, data, content_type="application/json")


def test_valid_ticket_shows_movie_room_and_seat(
    agent_client, agent, paid, screening
):
    """Critère 1 : écran vert avec le film, la salle et la place"""
    ticket = paid.tickets.first()

    response = scan(agent_client, screening, ticket_token(ticket))

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "VALID"
    assert data["ticket"]["seat"] == "A1"
    assert data["ticket"]["reference"] == paid.reference
    assert data["ticket"]["screening"]["room"] == "Salle test"
    assert data["ticket"]["screening"]["movie"]["title"] == "Film test"
    ticket.refresh_from_db()
    assert ticket.scanned_at is not None
    assert ticket.scanned_by == agent


def test_scan_answers_in_less_than_one_second(agent_client, paid, screening):
    """Critère 1 : réponse en moins d'une seconde"""
    code = ticket_token(paid.tickets.first())

    start = time.perf_counter()
    scan(agent_client, screening, code)

    assert time.perf_counter() - start < 1


def test_already_scanned_ticket_shows_first_passage(
    agent_client, paid, screening
):
    """Critère 2 : écran rouge avec l'heure du 1er passage"""
    ticket = paid.tickets.first()
    scan(agent_client, screening, ticket_token(ticket))
    ticket.refresh_from_db()
    first_passage = ticket.scanned_at

    response = scan(agent_client, screening, ticket_token(ticket))

    data = response.json()
    assert data["result"] == "ALREADY_SCANNED"
    ticket.refresh_from_db()
    assert ticket.scanned_at == first_passage  # heure non modifiée
    assert data["ticket"]["scanned_at"] is not None


def test_ticket_for_another_screening(agent_client, paid, movie, room):
    """Critère 3 : écran orange pour une autre séance ou une autre date"""
    other = Screening.objects.create(
        movie=movie, room=room, starts_at=timezone.now() + timedelta(days=2)
    )
    ticket = paid.tickets.first()

    response = scan(agent_client, other, ticket_token(ticket))

    data = response.json()
    assert data["result"] == "OTHER_SCREENING"
    # La séance du billet est affichée pour orienter le spectateur
    assert data["ticket"]["screening"]["id"] == paid.screening.pk
    ticket.refresh_from_db()
    assert ticket.scanned_at is None


def test_forged_code_is_invalid(agent_client, paid, screening):
    """Un QR code sans la bonne signature est refusé (US 4.1)"""
    ticket = paid.tickets.first()

    response = scan(agent_client, screening, f"{ticket.pk}:fausse-signature")

    assert response.json() == {"result": "INVALID", "ticket": None}
    ticket.refresh_from_db()
    assert ticket.scanned_at is None


def test_unpaid_ticket_is_invalid(agent_client, screening, seats, price):
    """Un billet seulement bloqué (pas payé) ne donne pas l'entrée"""
    booking = hold_seats(screening, seats[2:3])

    code = ticket_token(booking.tickets.first())
    response = scan(agent_client, screening, code)

    assert response.json()["result"] == "INVALID"


def test_only_box_office_staff_can_scan(client, make_user, paid, screening):
    """Le contrôle est réservé au personnel de l'accueil (US 9.1)"""
    code = ticket_token(paid.tickets.first())

    assert scan(client, screening, code).status_code == 401
    client.force_login(make_user(User.Role.MANAGEMENT))
    assert scan(client, screening, code).status_code == 403


def test_entries_of_the_screening(agent_client, paid, screening, seats):
    """Critère 4 : liste de la séance chargée avant une coupure réseau"""
    hold_seats(screening, seats[2:3])  # en attente de paiement : absente

    response = agent_client.get(
        f"/api/tickets/screenings/{screening.pk}/entries/"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(paid.pk),
            "reference": paid.reference,
            "seats": ["A1", "A2"],
            "scanned_at": None,
        }
    ]


def test_checkin_validates_the_whole_booking(agent_client, paid, screening):
    """Critère 4 : entrée validée par le numéro de réservation"""
    response = agent_client.post(f"/api/tickets/bookings/{paid.pk}/checkin/")

    assert response.status_code == 200
    assert response.json()["scanned_at"] is not None
    assert not paid.tickets.filter(scanned_at__isnull=True).exists()
    # Le QR code d'un billet de cette réservation est alors déjà utilisé
    code = ticket_token(paid.tickets.first())
    assert scan(agent_client, screening, code).json()["result"] == (
        "ALREADY_SCANNED"
    )


def test_checkin_keeps_the_first_passage(agent_client, paid, screening):
    """Une entrée validée plus tard garde l'heure du 1er passage"""
    ticket = paid.tickets.first()
    scan(agent_client, screening, ticket_token(ticket))
    ticket.refresh_from_db()
    first_passage = ticket.scanned_at
    assert first_passage is not None

    agent_client.post(f"/api/tickets/bookings/{paid.pk}/checkin/")

    ticket.refresh_from_db()
    assert ticket.scanned_at == first_passage
