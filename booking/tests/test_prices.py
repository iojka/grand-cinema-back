"""Tests du choix du tarif de chaque place (US 2.3)"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from booking.models import Booking
from booking.services import hold_seats
from programme.models import Price

pytestmark = pytest.mark.django_db


@pytest.fixture
def basket(screening, seats, price):
    """Panier en cours : A1 et A2 bloquées dans une salle à +2 €"""
    room = screening.room
    room.supplement = Decimal("2.00")
    room.save()
    return hold_seats(screening, seats[:2])


@pytest.fixture
def reduced():
    """Tarif réduit à 8,50 €, avec justificatif demandé à l'entrée"""
    return Price.objects.create(
        label="Tarif réduit", amount=Decimal("8.50"), requires_proof=True
    )


def url(booking):
    """Adresse du panier (réservation en attente)"""
    return f"/api/booking/bookings/{booking.pk}/"


def change_price(client, booking, ticket, price):
    """Choisit le tarif d'une place du panier"""
    return client.patch(
        f"{url(booking)}tickets/{ticket.pk}/",
        {"price": price.pk},
        content_type="application/json",
    )


def test_basket_shows_tickets_and_total(client, basket):
    """Le panier affiche les places, leur prix et le total"""
    data = client.get(url(basket)).json()

    assert [ticket["seat"] for ticket in data["tickets"]] == ["A1", "A2"]
    assert data["total_amount"] == "26.00"  # 2 x (11 + 2)


def test_only_active_prices_are_proposed(client, basket, reduced):
    """Critères 1 et 3 : seuls les tarifs actifs, au même prix qu'au guichet"""
    Price.objects.create(
        label="Ancien tarif", amount=Decimal("5.00"), is_active=False
    )

    prices = client.get(url(basket)).json()["prices"]

    labels = [item["label"] for item in prices]
    assert labels == ["Plein tarif", "Tarif réduit"]
    # Même calcul qu'au guichet : tarif + supplément de la salle (US 6.2)
    assert prices[1]["amount"] == str(
        reduced.amount_for(basket.screening.room)
    )
    assert prices[1]["requires_proof"] is True


def test_changing_a_price_recalculates_the_total(client, basket, reduced):
    """Critère 2 : le total est recalculé, supplément compris"""
    ticket = basket.tickets.first()

    response = change_price(client, basket, ticket, reduced)

    assert response.status_code == 200
    assert response.json()["total_amount"] == "23.50"  # 13 + 10,50
    ticket.refresh_from_db()
    assert ticket.unit_price == Decimal("10.50")


def test_inactive_price_is_refused(client, basket):
    """Critère 1 : un tarif désactivé par Isabelle est refusé"""
    old = Price.objects.create(
        label="Ancien tarif", amount=Decimal("5.00"), is_active=False
    )

    response = change_price(client, basket, basket.tickets.first(), old)

    assert response.status_code == 400


def test_expired_basket_cannot_be_changed(client, basket, reduced):
    """Après 10 minutes, le panier n'existe plus : erreur 404"""
    ticket = basket.tickets.first()
    basket.expires_at = timezone.now() - timedelta(minutes=1)
    basket.save()

    response = change_price(client, basket, ticket, reduced)

    assert response.status_code == 404


def test_cancelled_basket_releases_its_seats(client, basket):
    """Critère 2 : changer de places annule le panier et libère ses places"""
    response = client.delete(url(basket))

    assert response.status_code == 204
    basket.refresh_from_db()
    assert basket.status == Booking.Status.CANCELLED
    assert basket.tickets.count() == 0


def test_expired_basket_cannot_be_cancelled(client, basket):
    """Un panier expiré n'existe plus : erreur 404"""
    basket.expires_at = timezone.now() - timedelta(minutes=1)
    basket.save()

    response = client.delete(url(basket))

    assert response.status_code == 404
