"""Tests des données de démonstration (commande seed_demo)"""

from datetime import datetime, time, timedelta

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from programme.models import Movie, Room, Screening

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_movies_and_screenings():
    """4 films et 2 séances par jour pour chacun, sans doublon"""
    call_command("seed_cinema")

    call_command("seed_demo", days=3)
    call_command("seed_demo", days=3)

    assert Movie.objects.count() == 4
    assert Screening.objects.count() == 4 * 2 * 3
    assert Movie.objects.filter(is_young_audience=True).count() == 1


def test_seed_demo_needs_the_rooms():
    """Sans les salles de seed_cinema, la commande s'arrête"""
    with pytest.raises(CommandError):
        call_command("seed_demo", days=1)


def test_seed_demo_skips_a_busy_slot(movie):
    """Un créneau déjà occupé est ignoré, sans arrêter la commande"""
    call_command("seed_cinema")
    tomorrow = timezone.localdate() + timedelta(days=1)
    Screening.objects.create(
        movie=movie,
        room=Room.objects.get(name="Salle 3"),
        starts_at=timezone.make_aware(datetime.combine(tomorrow, time(20, 0))),
    )

    call_command("seed_demo", days=3)

    # 24 séances prévues, moins celle de 20 h 30 qui chevauche, plus la
    # séance déjà en place
    assert Screening.objects.count() == 24
