"""Tests de la vente au guichet sur le stock unique de places (US 7.2)"""

import threading

import pytest
from django.db import connection
from django.test import Client

from accounts.models import User
from booking.models import Booking, Ticket
from booking.services import hold_seats

pytestmark = pytest.mark.django_db

URL = "/api/booking/box-office/sales/"


@pytest.fixture
def agent(make_user):
    """Agent d'accueil du guichet"""
    return make_user(User.Role.BOX_OFFICE)


@pytest.fixture
def agent_client(client, agent):
    """Client de test connecté avec le compte de l'agent d'accueil"""
    client.force_login(agent)
    return client


def sell(client, screening, seats, price, method="CASH"):
    """Vente au guichet : une place = un tarif, puis le mode de paiement"""
    tickets = [{"seat": seat.pk, "price": price.pk} for seat in seats]
    data = {
        "screening": screening.pk,
        "tickets": tickets,
        "payment_method": method,
    }
    return client.post(URL, data, content_type="application/json")


def seat_map(client, screening):
    """Plan de salle public, celui du site"""
    return client.get(f"/api/booking/screenings/{screening.pk}/seats/")


def test_sale_records_the_payment_method(
    agent_client, agent, screening, seats, price
):
    """Critère 4 : vente confirmée, mode de paiement et agent enregistrés"""
    response = sell(agent_client, screening, seats[:2], price, "CARD_TERMINAL")

    assert response.status_code == 201
    booking = Booking.objects.get(pk=response.json()["id"])
    assert booking.channel == Booking.Channel.BOX_OFFICE
    assert booking.status == Booking.Status.CONFIRMED
    assert booking.payment_method == Booking.PaymentMethod.CARD_TERMINAL
    assert booking.sold_by == agent
    assert booking.total_amount == 22  # 2 places au plein tarif de 11 €
    assert booking.tickets.filter(status=Ticket.Status.SOLD).count() == 2


def test_printed_ticket_with_qr_code(agent_client, screening, seats, price):
    """Critère 4 : le billet à imprimer (QR code, US 4.2) est disponible"""
    response = sell(agent_client, screening, seats[:1], price)

    booking_id = response.json()["id"]
    pdf = agent_client.get(f"/api/tickets/bookings/{booking_id}/pdf/")
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"


def test_online_payment_method_is_refused(
    agent_client, screening, seats, price
):
    """Au guichet : espèces ou carte via le terminal de paiement"""
    response = sell(agent_client, screening, seats[:1], price, "ONLINE_CARD")

    assert response.status_code == 400


def test_sold_seat_is_unavailable_online(
    agent_client, screening, seats, price
):
    """Critère 1 : la place vendue au guichet est prise sur le site"""
    sell(agent_client, screening, seats[:1], price)

    data = seat_map(Client(), screening).json()

    assert data["seats"][0]["status"] == Ticket.Status.SOLD


def test_seat_map_shows_the_same_prices(client, screening, seats, price):
    """Critère 3 : même plan de salle et mêmes tarifs que le site"""
    data = seat_map(client, screening).json()

    assert data["prices"] == [
        {
            "id": price.pk,
            "label": "Plein tarif",
            "amount": "11.00",
            "requires_proof": False,
        }
    ]


def test_seat_held_online_cannot_be_sold(
    agent_client, screening, seats, price
):
    """Une place déjà bloquée en ligne est refusée au guichet (409)"""
    hold_seats(screening, seats[:1])

    response = sell(agent_client, screening, seats[:1], price)

    assert response.status_code == 409
    assert "detail" in response.json()


def test_only_box_office_staff_can_sell(
    client, make_user, screening, seats, price
):
    """Vente réservée au personnel du guichet (US 9.1)"""
    assert sell(client, screening, seats[:1], price).status_code == 401

    client.force_login(make_user(User.Role.MANAGEMENT))
    assert sell(client, screening, seats[:1], price).status_code == 403


@pytest.mark.django_db(transaction=True)
def test_only_one_of_online_and_box_office_sales_succeeds(
    agent, screening, seats, price
):
    """Critère 2 : test de concurrence, site et guichet, une même place"""
    results = []
    start = threading.Barrier(2)  # les deux demandes partent ensemble

    def spectator():
        start.wait()
        data = {"screening": screening.pk, "seats": [seats[0].pk]}
        response = Client().post(
            "/api/booking/holds/", data, content_type="application/json"
        )
        results.append(response.status_code)
        connection.close()  # chaque thread ferme sa connexion à la base

    def box_office():
        client = Client()
        client.force_login(agent)
        start.wait()
        response = sell(client, screening, seats[:1], price)
        results.append(response.status_code)
        connection.close()

    threads = [
        threading.Thread(target=spectator),
        threading.Thread(target=box_office),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [201, 409]
    assert Ticket.objects.filter(seat=seats[0]).count() == 1
