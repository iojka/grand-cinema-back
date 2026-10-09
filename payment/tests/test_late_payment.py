"""Correctif D3 Q3 : paiement reçu après la fin du blocage (US 3.1)

Scénario du bug : le spectateur paie sur la page Stripe après ses
10 minutes de blocage ; entre-temps ses places ont été libérées. La
notification « payé » arrive : il est débité sans place ni billet.
Stripe est remplacé par des doubles de test (unittest.mock)
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from booking.models import Booking, Ticket
from booking.services import hold_seats, release_expired_bookings

pytestmark = pytest.mark.django_db

URL = "/api/payment/webhook/"
CONSTRUCT_EVENT = "payment.views.stripe.Webhook.construct_event"
REFUND = "payment.services.stripe.Refund.create"


@pytest.fixture
def basket(screening, seats, price):
    """Panier envoyé au paiement, dont le blocage de 10 minutes est fini"""
    booking = hold_seats(screening, seats[:2])
    booking.customer_name = "Marine Crognier"
    booking.customer_email = "marine@example.com"
    booking.customer_postcode = "48000"
    booking.stripe_session_id = "cs_test_late"
    booking.expires_at = timezone.now() - timedelta(minutes=1)
    booking.save()
    return booking


def notify_paid(client):
    """Simule la notification signée « paiement accepté » de Stripe"""
    event = {
        "id": "evt_test_late",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_late",
                "payment_status": "paid",
                "payment_intent": "pi_test_late",
            }
        },
    }
    with patch(CONSTRUCT_EVENT, return_value=event):
        return client.post(
            URL,
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=signature",
        )


def test_late_payment_is_refunded(client, basket):
    """Places déjà libérées : le paiement est remboursé automatiquement"""
    # Un autre spectateur consulte le plan : le blocage expiré est libéré
    release_expired_bookings()

    with patch(REFUND) as refund:
        response = notify_paid(client)

    assert response.status_code == 200
    refund.assert_called_once_with(payment_intent="pi_test_late")
    basket.refresh_from_db()
    assert basket.status == Booking.Status.EXPIRED
    assert len(mail.outbox) == 0  # pas de confirmation sans places


def test_late_payment_with_seats_still_held_is_confirmed(client, basket):
    """Non-régression : places pas encore libérées, la vente est confirmée

    Les billets existent encore : personne n'a pu prendre ces places
    """
    with patch(REFUND) as refund:
        notify_paid(client)

    refund.assert_not_called()
    basket.refresh_from_db()
    assert basket.status == Booking.Status.CONFIRMED
    assert basket.tickets.filter(status=Ticket.Status.SOLD).count() == 2
