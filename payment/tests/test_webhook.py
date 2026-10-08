"""Tests de la notification signée envoyée par Stripe (US 3.1)

La vérification de signature de Stripe est remplacée par un double de
test (unittest.mock) : on choisit l'événement « reçu »
"""

from unittest.mock import patch

import pytest
import stripe

from booking.models import Booking, Ticket
from booking.services import hold_seats
from payment.models import StripeEvent

pytestmark = pytest.mark.django_db

URL = "/api/payment/webhook/"
CONSTRUCT_EVENT = "payment.views.stripe.Webhook.construct_event"


@pytest.fixture
def basket(screening, seats, price):
    """Panier envoyé au paiement : session Stripe cs_test_123"""
    booking = hold_seats(screening, seats[:2])
    booking.customer_name = "Marine Crognier"
    booking.customer_email = "marine@example.com"
    booking.customer_postcode = "48000"
    booking.stripe_session_id = "cs_test_123"
    booking.save()
    return booking


def paid_event(event_id="evt_test_1"):
    """Événement « paiement accepté » tel que Stripe l'envoie"""
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_123", "payment_status": "paid"}},
    }


def notify(client, event):
    """Simule l'appel de Stripe avec une signature acceptée"""
    with patch(CONSTRUCT_EVENT, return_value=event):
        return client.post(
            URL,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=signature",
        )


def test_paid_event_confirms_the_booking(client, basket):
    """Critère 4 : la notification signée confirme la réservation"""
    response = notify(client, paid_event())

    assert response.status_code == 200
    basket.refresh_from_db()
    assert basket.status == Booking.Status.CONFIRMED
    assert basket.payment_method == Booking.PaymentMethod.ONLINE_CARD
    assert basket.confirmed_at is not None
    assert basket.tickets.filter(status=Ticket.Status.SOLD).count() == 2


def test_same_event_is_processed_only_once(client, basket):
    """Critère 4 : reçue deux fois, la notification est traitée une fois"""
    notify(client, paid_event())
    basket.refresh_from_db()
    first_confirmation = basket.confirmed_at

    response = notify(client, paid_event())

    assert response.status_code == 200
    assert StripeEvent.objects.count() == 1
    basket.refresh_from_db()
    assert basket.confirmed_at == first_confirmation


def test_no_card_data_is_stored(client, basket):
    """Critère 2 : le journal ne garde que des identifiants Stripe"""
    notify(client, paid_event())

    saved = StripeEvent.objects.values().first()
    assert set(saved) == {
        "id",
        "event_id",
        "event_type",
        "received_at",
        "booking_id",
    }


def test_bad_signature_is_refused(client, basket):
    """Une notification mal signée (pas envoyée par Stripe) est refusée"""
    error = stripe.SignatureVerificationError("signature invalide", "t=1")
    with patch(CONSTRUCT_EVENT, side_effect=error):
        response = client.post(
            URL,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=fausse",
        )

    assert response.status_code == 400
    basket.refresh_from_db()
    assert basket.status == Booking.Status.PENDING
