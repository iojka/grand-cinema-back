"""Tests de la permission par rôle de l'API (US 9.1, critère 2)"""

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from accounts.models import User
from accounts.permissions import HasRole

pytestmark = pytest.mark.django_db


class FakeView:
    """Vue de test réservée aux agents d'accueil"""

    allowed_roles = [User.Role.BOX_OFFICE]


def make_request(user):
    """Prépare une requête GET envoyée par l'utilisateur donné"""
    request = APIRequestFactory().get("/")
    request.user = user
    return request


def test_allowed_role_has_access(make_user):
    """Un rôle listé dans la vue a accès"""
    request = make_request(make_user(User.Role.BOX_OFFICE))

    assert HasRole().has_permission(request, FakeView())


def test_other_role_is_refused(make_user):
    """Un rôle absent de la liste est refusé"""
    request = make_request(make_user(User.Role.MANAGEMENT))

    assert not HasRole().has_permission(request, FakeView())


def test_anonymous_is_refused():
    """Un visiteur non connecté est refusé"""
    request = make_request(AnonymousUser())

    assert not HasRole().has_permission(request, FakeView())
