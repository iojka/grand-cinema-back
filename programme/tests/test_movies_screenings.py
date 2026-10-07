"""Tests de la création des films et des séances (US 6.1)"""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from programme.models import Movie, Screening

pytestmark = pytest.mark.django_db


def screening_form(movie, room, starts_at):
    """Prépare les données du formulaire de séance de l'admin

    :return: un dictionnaire comme celui envoyé par le navigateur
    """
    local_start = timezone.localtime(starts_at)
    return {
        "movie": movie.pk,
        "room": room.pk,
        "starts_at_0": f"{local_start:%Y-%m-%d}",
        "starts_at_1": f"{local_start:%H:%M:%S}",
        "status": Screening.Status.SCHEDULED,
    }


def test_programming_creates_a_movie(client, make_user):
    """Critère 1 : Isabelle crée un film avec toutes ses informations"""
    client.force_login(make_user(User.Role.PROGRAMMING))

    response = client.post(
        reverse("admin:programme_movie_add"),
        {
            "title": "Le jazz à Mende",
            "synopsis": "Un documentaire sur le festival de jazz.",
            "duration_minutes": 95,
            "rating": Movie.Rating.ALL,
            "version": Movie.Version.VF,
            "is_young_audience": "on",
        },
    )

    assert response.status_code == 302
    movie = Movie.objects.get(title="Le jazz à Mende")
    assert movie.is_young_audience


def test_movie_duration_is_checked_by_the_database():
    """Dette D1 Q2 : une durée de 0 minute est refusée par la base"""
    with pytest.raises(IntegrityError):
        Movie.objects.create(
            title="Film vide",
            synopsis="Film sans durée",
            duration_minutes=0,
            version=Movie.Version.VF,
        )


def test_new_screening_is_published_immediately(
    client, make_user, movie, room
):
    """Critère 2 : une séance créée est programmée tout de suite"""
    client.force_login(make_user(User.Role.PROGRAMMING))
    starts_at = timezone.now() + timedelta(days=2)

    response = client.post(
        reverse("admin:programme_screening_add"),
        screening_form(movie, room, starts_at),
    )

    assert response.status_code == 302
    screening = Screening.objects.get(movie=movie, room=room)
    assert screening.status == Screening.Status.SCHEDULED


def test_overlap_is_refused_in_admin_with_a_message(
    client, make_user, screening
):
    """Critère 3 : la séance qui chevauche est refusée avec un message"""
    client.force_login(make_user(User.Role.PROGRAMMING))
    starts_at = screening.starts_at + timedelta(minutes=30)

    response = client.post(
        reverse("admin:programme_screening_add"),
        screening_form(screening.movie, screening.room, starts_at),
    )

    # Le formulaire est réaffiché avec le message d'erreur
    assert response.status_code == 200
    assert "chevauche" in response.content.decode()
    assert Screening.objects.count() == 1


def test_overlap_is_refused_even_outside_the_admin(screening):
    """Critère 3 (dette D1 Q2) : la règle s'applique aussi hors admin"""
    with pytest.raises(ValidationError):
        Screening.objects.create(
            movie=screening.movie,
            room=screening.room,
            starts_at=screening.starts_at + timedelta(minutes=30),
        )


def test_screening_with_bookings_cannot_be_deleted(make_booking, screening):
    """Critère 4 : une séance avec des réservations n'est pas supprimée"""
    make_booking()

    with pytest.raises(ProtectedError):
        screening.delete()


def test_admin_keeps_a_screening_with_bookings(
    client, make_user, make_booking, screening
):
    """Critère 4 : dans l'admin, la suppression est refusée"""
    make_booking()
    client.force_login(make_user(User.Role.PROGRAMMING))

    client.post(
        reverse("admin:programme_screening_delete", args=[screening.pk]),
        {"post": "yes"},
    )

    assert Screening.objects.filter(pk=screening.pk).exists()
