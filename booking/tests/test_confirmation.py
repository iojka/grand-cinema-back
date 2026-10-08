"""Tests du récapitulatif de la réservation payée (US 3.3)"""

import pytest

from booking.models import Booking
from booking.services import cancel_booking, hold_seats

pytestmark = pytest.mark.django_db


@pytest.fixture
def basket(screening, seats, price):
    """Réservation de 2 places en attente du paiement"""
    return hold_seats(screening, seats[:2])


@pytest.fixture
def paid(basket):
    """Réservation payée : confirmée par la notification de Stripe"""
    basket.customer_email = "marine@example.com"
    basket.status = Booking.Status.CONFIRMED
    basket.save()
    return basket


def get_confirmation(client, booking):
    """Lit le récapitulatif de la réservation"""
    return client.get(f"/api/booking/bookings/{booking.pk}/confirmation/")


def test_confirmation_sums_up_the_booking(client, paid):
    """Critère 1 : film, date et heure, salle, places, montant, numéro"""
    response = get_confirmation(client, paid)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CONFIRMED"
    assert data["reference"] == paid.reference
    assert data["screening"]["movie"]["title"] == "Film test"
    assert data["screening"]["room"] == "Salle test"
    assert data["screening"]["starts_at"] is not None
    assert [ticket["seat"] for ticket in data["tickets"]] == ["A1", "A2"]
    assert data["total_amount"] == "22.00"


def test_no_personal_data_in_the_confirmation(client, paid):
    """Minimisation (RGPD) : les coordonnées ne sont pas renvoyées"""
    data = get_confirmation(client, paid).json()

    assert "customer_email" not in data


def test_payment_not_yet_confirmed(client, basket):
    """Stripe n'a pas encore confirmé : la page affiche l'attente"""
    response = get_confirmation(client, basket)

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"


def test_cancelled_booking_has_no_confirmation(client, basket):
    """Critère 3 : un parcours arrêté n'a pas de confirmation"""
    cancel_booking(basket)

    response = get_confirmation(client, basket)

    assert response.status_code == 404
