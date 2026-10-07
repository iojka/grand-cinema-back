"""Tests de l'API de la fiche film (US 1.3)"""

import pytest

from programme.models import Movie, Screening
from programme.tests.test_api_programme import at

pytestmark = pytest.mark.django_db


def url(movie_id):
    """Adresse de la fiche d'un film"""
    return f"/api/programme/movies/{movie_id}/"


def test_movie_page_shows_all_details(client, movie):
    """Critère 1 : titre, affiche, synopsis, durée, classification, version"""
    response = client.get(url(movie.pk))

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Film test"
    assert data["synopsis"] == "Synopsis du film de test."
    assert data["duration_minutes"] == 120
    assert data["rating"] == Movie.Rating.ALL
    assert data["version"] == Movie.Version.VF


def test_movie_without_poster_has_no_image(client, movie):
    """Critère 3 : sans affiche, le front affichera un visuel par défaut"""
    data = client.get(url(movie.pk)).json()

    assert data["poster"] is None


def test_movie_page_lists_next_screenings(client, movie, room):
    """Critère 1 et 2 : prochaines séances triées, avec leur identifiant"""
    later = Screening.objects.create(
        movie=movie, room=room, starts_at=at(2, 20)
    )
    first = Screening.objects.create(
        movie=movie, room=room, starts_at=at(1, 14)
    )
    # Pas affichées : déjà passée, dans plus de 7 jours, annulée
    Screening.objects.create(movie=movie, room=room, starts_at=at(-1, 20))
    Screening.objects.create(movie=movie, room=room, starts_at=at(9, 20))
    Screening.objects.create(
        movie=movie,
        room=room,
        starts_at=at(3, 20),
        status=Screening.Status.CANCELLED,
    )

    screenings = client.get(url(movie.pk)).json()["screenings"]

    assert [item["id"] for item in screenings] == [first.pk, later.pk]
    assert screenings[0]["room"] == "Salle test"
    # Salle de test sans places : la séance est complète
    assert screenings[0]["is_full"] is True


def test_unknown_movie_returns_404(client):
    """Un film qui n'existe pas renvoie une erreur 404"""
    response = client.get(url(9999))

    assert response.status_code == 404
