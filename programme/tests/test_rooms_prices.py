"""Tests du paramétrage des salles, des plans et des tarifs (US 6.2)"""

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import reverse

from accounts.models import User
from booking.models import Booking, Ticket
from programme.models import Price, Room, Seat

pytestmark = pytest.mark.django_db


def test_seed_creates_the_10_rooms_of_the_b1():
    """Critère 1 : 2 x 300, 4 x 180, 2 x 120 et 2 x 70, soit 1 700 places"""
    call_command("seed_cinema")

    capacities = {}
    for room in Room.objects.all():
        capacities.setdefault(room.category, []).append(room.capacity)

    assert capacities[Room.Category.PREMIUM] == [300, 300]
    assert capacities[Room.Category.STANDARD] == [180, 180, 180, 180]
    assert capacities[Room.Category.VIP] == [120, 120]
    assert capacities[Room.Category.EVENT] == [70, 70]
    assert sum(sum(values) for values in capacities.values()) == 1700


def test_new_room_plan_is_used_for_upcoming_screenings(screening, seats):
    """Critère 2 : le plan modifié s'applique aux séances à venir"""
    room = screening.room
    # Isabelle retire une place et ajoute une place PMR en rangée B
    seats[0].is_active = False
    seats[0].save()
    Seat.objects.create(room=room, row="B", number=1, is_accessible=True)

    active_seats = screening.room.seats.filter(is_active=True)
    assert screening.room.capacity == 4
    assert active_seats.filter(is_accessible=True).count() == 1


def test_programming_can_edit_a_room_plan(client, make_user, room, seats):
    """Critère 2 : Isabelle modifie le plan de la salle dans l'admin"""
    client.force_login(make_user(User.Role.PROGRAMMING))

    response = client.get(
        reverse("admin:programme_room_change", args=[room.pk])
    )

    assert response.status_code == 200
    # Les places de la salle sont modifiables sur la même page
    assert len(response.context["inline_admin_formsets"]) == 1


def test_new_price_applies_to_new_bookings(price, room):
    """Critère 3 : un tarif modifié s'applique aux nouvelles réservations"""
    price.amount = Decimal("12.00")
    price.save()

    assert price.amount_for(room) == Decimal("12.00")


def test_room_supplement_is_added_to_the_price(price, room):
    """Critère 3 : le supplément IMAX / VIP s'ajoute au tarif"""
    room.supplement = Decimal("5.00")
    room.save()

    assert price.amount_for(room) == Decimal("16.00")


def test_price_change_does_not_change_paid_tickets(make_booking, seats, price):
    """Critère 4 : les réservations déjà payées ne sont pas impactées"""
    booking = make_booking(status=Booking.Status.CONFIRMED)
    ticket = Ticket.objects.create(
        booking=booking,
        screening=booking.screening,
        seat=seats[0],
        price=price,
        unit_price=price.amount_for(booking.screening.room),
        status=Ticket.Status.SOLD,
    )

    price.amount = Decimal("13.00")
    price.save()

    ticket.refresh_from_db()
    assert ticket.unit_price == Decimal("11.00")


def test_seed_does_not_overwrite_isabelle_changes():
    """Dette relevée en D1 Q2 : relancer le seed garde les modifications"""
    call_command("seed_cinema")
    full_price = Price.objects.get(label="Plein tarif")
    full_price.amount = Decimal("11.50")
    full_price.save()
    imax = Room.objects.get(name="Salle 1 - IMAX")
    imax.supplement = Decimal("4.00")
    imax.save()

    call_command("seed_cinema")

    assert Price.objects.get(label="Plein tarif").amount == Decimal("11.50")
    assert Room.objects.get(name="Salle 1 - IMAX").supplement == Decimal("4")
