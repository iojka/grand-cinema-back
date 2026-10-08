"""Tests de la redirection vers la page de paiement Stripe (US 3.1)

Stripe n'est jamais appelé pendant les tests : unittest.mock remplace
l'appel par une réponse préparée (double de test)
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from booking.services import hold_seats

pytestmark = pytest.mark.django_db

STRIPE_CREATE = "payment.services.stripe.checkout.Session.create"


@pytest.fixture
def basket(screening, seats, price):
    """Panier validé : 2 places et les coordonnées du spectateur"""
    booking = hold_seats(screening, seats[:2])
    booking.customer_name = "Marine Crognier"
    booking.customer_email = "marine@example.com"
    booking.customer_postcode = "48000"
    booking.save()
    return booking


def url(booking):
    """Adresse qui démarre le paiement du panier"""
    return f"/api/payment/bookings/{booking.pk}/checkout/"


def fake_session():
    """Session de paiement renvoyée par Stripe (simulée)"""
    session = MagicMock()
    session.id = "cs_test_123"
    session.url = "https://checkout.stripe.com/c/pay/cs_test_123"
    return session


def test_paying_redirects_to_the_stripe_page(client, basket):
    """Critère 1 : le spectateur est envoyé vers la page sécurisée Stripe"""
    with patch(STRIPE_CREATE, return_value=fake_session()) as create:
        response = client.post(url(basket))

    assert response.status_code == 200
    assert response.json()["url"].startswith("https://checkout.stripe.com/")
    # Montant de chaque place en centimes, en euros, e-mail prérempli
    options = create.call_args.kwargs
    assert options["mode"] == "payment"
    assert options["customer_email"] == "marine@example.com"
    lines = options["line_items"]
    amounts = [line["price_data"]["unit_amount"] for line in lines]
    assert amounts == [1100, 1100]
    assert options["line_items"][0]["price_data"]["currency"] == "eur"


def test_only_the_stripe_session_id_is_kept(client, basket):
    """Critère 2 : seul l'identifiant de la session Stripe est enregistré"""
    with patch(STRIPE_CREATE, return_value=fake_session()):
        client.post(url(basket))

    basket.refresh_from_db()
    assert basket.stripe_session_id == "cs_test_123"


def test_customer_details_are_needed_before_paying(client, basket):
    """Le paiement suit l'étape des coordonnées (US 2.4)"""
    basket.customer_email = ""
    basket.save()

    with patch(STRIPE_CREATE) as create:
        response = client.post(url(basket))

    assert response.status_code == 400
    create.assert_not_called()


def test_expired_basket_cannot_be_paid(client, basket):
    """Après 10 minutes, le panier n'existe plus : erreur 404"""
    basket.expires_at = timezone.now() - timedelta(minutes=1)
    basket.save()

    with patch(STRIPE_CREATE) as create:
        response = client.post(url(basket))

    assert response.status_code == 404
    create.assert_not_called()
