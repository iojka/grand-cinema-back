"""Données de test du module tickets (fixtures pytest)"""

import pytest

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
