"""Tests du programme : places, salles, séances et données de référence."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from programme.models import Price, Room, Screening, Seat

pytestmark = pytest.mark.django_db


def test_seat_position_is_unique_in_a_room(room):
    """Une salle ne peut pas avoir deux fois la place A1."""
    Seat.objects.create(room=room, row="A", number=1)

    with pytest.raises(IntegrityError):
        Seat.objects.create(room=room, row="A", number=1)


def test_room_capacity_counts_only_active_seats(room, seats):
    """Une place retirée du plan n'est plus comptée dans la capacité."""
    seats[0].is_active = False
    seats[0].save()

    assert room.capacity == 3


def test_screening_end_is_start_plus_movie_duration(screening):
    """La fin de la séance = début + durée du film (2 h)."""
    duration = screening.ends_at - screening.starts_at

    assert duration == timedelta(minutes=120)


def test_overlapping_screening_in_same_room_is_refused(screening, movie, room):
    """US 6.1 : 2 h 10 après une séance de 2 h, la marge n'y est pas."""
    overlapping = Screening(
        movie=movie,
        room=room,
        starts_at=screening.starts_at + timedelta(minutes=130),
    )

    with pytest.raises(ValidationError):
        overlapping.full_clean()


def test_screening_after_cleaning_margin_is_accepted(screening, movie, room):
    """US 6.1 : 2 h 15 après une séance de 2 h, la séance est acceptée."""
    following = Screening(
        movie=movie,
        room=room,
        starts_at=screening.starts_at + timedelta(minutes=135),
    )

    following.full_clean()  # aucune exception levée


def test_same_time_in_another_room_is_accepted(screening, movie):
    """Deux séances à la même heure dans deux salles sont possibles."""
    other_room = Room.objects.create(
        name="Autre salle", category=Room.Category.VIP
    )
    parallel = Screening(
        movie=movie, room=other_room, starts_at=screening.starts_at
    )

    parallel.full_clean()  # aucune exception levée


def test_seed_creates_10_rooms_1700_seats_and_can_be_run_twice():
    """Le jeu de données du B1 est complet et sans doublon si relancé."""
    call_command("seed_cinema")
    call_command("seed_cinema")

    assert Room.objects.count() == 10
    assert Seat.objects.filter(is_active=True).count() == 1700
    assert Price.objects.count() == 3
    assert Room.objects.get(name="Salle 7 - VIP").capacity == 120
