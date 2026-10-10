"""Tests des coordonnées du spectateur sans compte (US 2.4)"""

from datetime import timedelta

import pytest
from django.utils import timezone

from booking.services import hold_seats

pytestmark = pytest.mark.django_db

VALID = {
    "customer_name": "Marine Crognier",
    "customer_email": "marine@example.com",
    "email_confirmation": "marine@example.com",
    "customer_postcode": "48000",
    "customer_country": "",
}


@pytest.fixture
def basket(screening, seats, price):
    """Panier en cours : une place bloquée, sans coordonnées"""
    return hold_seats(screening, seats[:1])


def send(client, basket, **changes):
    """Envoie les coordonnées du panier (VALID modifié par changes)"""
    data = {**VALID, **changes}
    return client.patch(
        f"/api/booking/bookings/{basket.pk}/customer/",
        data,
        content_type="application/json",
    )


def test_customer_details_are_saved(client, basket):
    """Critère 2 : nom, e-mail et code postal suffisent"""
    response = send(client, basket)

    assert response.status_code == 200
    basket.refresh_from_db()
    assert basket.customer_name == "Marine Crognier"
    assert basket.customer_email == "marine@example.com"
    assert basket.customer_postcode == "48000"


def test_a_tourist_gives_his_country(client, basket):
    """Critère 2 : un touriste donne son pays à la place du code postal"""
    response = send(
        client, basket, customer_postcode="", customer_country="DE"
    )

    assert response.status_code == 200
    basket.refresh_from_db()
    assert basket.customer_country == "DE"


def test_postcode_or_country_is_needed(client, basket):
    """Critère 2 : il faut le code postal ou le pays"""
    response = send(client, basket, customer_postcode="", customer_country="")

    assert response.status_code == 400


def test_both_emails_must_match(client, basket):
    """Critère 2 : l'adresse e-mail est saisie deux fois à l'identique"""
    response = send(client, basket, email_confirmation="marine@exemple.com")

    assert response.status_code == 400


def test_invalid_email_is_refused(client, basket):
    """Critère 3 : une adresse e-mail non valide est signalée"""
    response = send(
        client,
        basket,
        customer_email="marine.example.com",
        email_confirmation="marine.example.com",
    )

    assert response.status_code == 400
    assert "customer_email" in response.json()


def test_name_is_needed(client, basket):
    """Critère 2 : le nom est obligatoire"""
    response = send(client, basket, customer_name="")

    assert response.status_code == 400


def test_expired_basket_cannot_be_completed(client, basket):
    """Après 10 minutes, le panier n'existe plus : erreur 404"""
    basket.expires_at = timezone.now() - timedelta(minutes=1)
    basket.save()

    response = send(client, basket)

    assert response.status_code == 404


def test_language_is_saved(client, basket):
    """US 3.3 : la langue du site sert à l'e-mail de confirmation"""
    response = send(client, basket, customer_language="en")

    assert response.status_code == 200
    basket.refresh_from_db()
    assert basket.customer_language == "en"


def test_unknown_language_is_refused(client, basket):
    """US 3.3 : seuls le français et l'anglais sont proposés"""
    response = send(client, basket, customer_language="de")

    assert response.status_code == 400
