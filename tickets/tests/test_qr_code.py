"""Tests du billet QR code (US 4.1)"""

import pytest
from django.core.signing import Signer

from booking.models import Booking, Ticket
from booking.services import hold_seats
from tickets.services import qr_code_png, ticket_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid(screening, seats, price):
    """Réservation payée de 2 places : billets vendus"""
    booking = hold_seats(screening, seats[:2])
    booking.customer_name = "Marine Crognier"
    booking.customer_email = "marine@example.com"
    booking.status = Booking.Status.CONFIRMED
    booking.save()
    booking.tickets.update(status=Ticket.Status.SOLD)
    return booking


def test_token_is_the_signed_ticket_id(paid):
    """Critère 4 : le QR code contient l'identifiant signé du billet"""
    ticket = paid.tickets.first()

    token = ticket_token(ticket)

    # Seul le serveur, qui connaît la clé secrète, peut vérifier
    assert Signer(salt="tickets").unsign(token) == str(ticket.pk)


def test_token_has_no_personal_data(paid):
    """Critère 4 : aucune donnée personnelle en clair"""
    token = ticket_token(paid.tickets.first())

    assert "Marine" not in token
    assert "marine@example.com" not in token


def test_each_ticket_has_its_own_qr_code(paid, screening, seats):
    """Critère 2 : 2 réservations distinctes, des QR codes tous différents"""
    other = hold_seats(screening, seats[2:3])

    tokens = {ticket_token(ticket) for ticket in paid.tickets.all()}
    tokens.add(ticket_token(other.tickets.first()))

    assert len(tokens) == 3


def test_qr_code_is_a_png_image(paid):
    """Le QR code est une image PNG (affichée, envoyée par e-mail)"""
    png = qr_code_png(paid.tickets.first())

    assert png.startswith(b"\x89PNG")


def test_qr_route_returns_the_image(client, paid):
    """Critère 1 : l'image du QR code est servie pour l'écran"""
    ticket = paid.tickets.first()

    response = client.get(f"/api/tickets/{ticket.pk}/qr/")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"


def test_no_qr_code_before_payment(client, screening, seats, price):
    """Pas de billet tant que le paiement n'est pas accepté"""
    basket = hold_seats(screening, seats[:1])
    ticket = basket.tickets.first()

    response = client.get(f"/api/tickets/{ticket.pk}/qr/")

    assert response.status_code == 404
