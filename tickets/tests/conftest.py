"""Données de test du module tickets (fixtures pytest)"""

import pytest

from accounts.models import User
from booking.models import Booking, Ticket
from booking.services import hold_seats


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


@pytest.fixture
def agent(make_user):
    """Agent d'accueil qui contrôle les billets à l'entrée (US 7.3)"""
    return make_user(User.Role.BOX_OFFICE)


@pytest.fixture
def agent_client(client, agent):
    """Client de test connecté avec le compte de l'agent d'accueil"""
    client.force_login(agent)
    return client
