"""Tests des réservations et du stock unique de places (US 2.2, 7.2)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from booking.models import REFERENCE_ALPHABET, Booking, Ticket
from programme.models import Room, Seat

pytestmark = pytest.mark.django_db


def make_ticket(booking, seat, price):
    """Crée un billet bloqué pour la séance de la réservation.

    :param booking: réservation à laquelle rattacher le billet
    :param seat: place réservée
    :param price: tarif appliqué
    :return: le billet créé
    """
    return Ticket.objects.create(
        booking=booking,
        screening=booking.screening,
        seat=seat,
        price=price,
        unit_price=Decimal("11.00"),
    )


def test_booking_gets_a_short_unique_reference(make_booking):
    """Chaque réservation reçoit une référence de 8 caractères lisibles."""
    first = make_booking()
    second = make_booking()

    assert len(first.reference) == 8
    assert set(first.reference) <= set(REFERENCE_ALPHABET)
    assert first.reference != second.reference


def test_same_seat_cannot_be_taken_twice_for_a_screening(
    make_booking, seats, price
):
    """Pas de double vente : une place vendue en ligne puis au guichet."""
    make_ticket(make_booking(), seats[0], price)
    box_office = make_booking(
        channel=Booking.Channel.BOX_OFFICE, customer_email=""
    )

    with pytest.raises(IntegrityError):
        make_ticket(box_office, seats[0], price)


def test_released_seat_can_be_booked_again(make_booking, seats, price):
    """Une place libérée après expiration du blocage redevient libre."""
    expired = make_booking()
    make_ticket(expired, seats[0], price)
    expired.tickets.all().delete()  # la tâche planifiée libère la place

    make_ticket(make_booking(), seats[0], price)  # aucune exception levée


def test_web_booking_requires_an_email(make_booking):
    """Une réservation en ligne sans e-mail est refusée par la base."""
    with pytest.raises(IntegrityError):
        make_booking(customer_email="")


def test_screening_with_bookings_cannot_be_deleted(make_booking, screening):
    """US 6.1 : une séance qui a des réservations ne peut être supprimée."""
    make_booking()

    with pytest.raises(ProtectedError):
        screening.delete()


def test_ticket_seat_must_belong_to_the_screening_room(make_booking, price):
    """Un billet ne peut pas porter sur une place d'une autre salle."""
    other_room = Room.objects.create(
        name="Autre salle", category=Room.Category.VIP
    )
    foreign_seat = Seat.objects.create(room=other_room, row="A", number=1)
    booking = make_booking()
    ticket = Ticket(
        booking=booking,
        screening=booking.screening,
        seat=foreign_seat,
        price=price,
        unit_price=Decimal("11.00"),
    )

    with pytest.raises(ValidationError):
        ticket.full_clean()
