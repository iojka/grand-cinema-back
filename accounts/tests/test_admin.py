"""Tests des droits dans l'admin Django (US 9.1)"""

import pytest
from django.urls import reverse

from accounts.admin import UserCreationForm
from accounts.models import User

pytestmark = pytest.mark.django_db


def test_admin_creates_account_with_a_role(client, make_user, password):
    """Critère 1 : l'administrateur crée un compte et lui donne un rôle"""
    admin = make_user(User.Role.ADMIN)
    client.force_login(admin)

    response = client.post(
        reverse("admin:accounts_user_add"),
        {
            "email": "isabelle@legrandcinema.test",
            "role": User.Role.PROGRAMMING,
            "usable_password": "true",
            "password1": password,
            "password2": password,
        },
    )

    assert response.status_code == 302
    isabelle = User.objects.get(email="isabelle@legrandcinema.test")
    assert isabelle.role == User.Role.PROGRAMMING


def test_admin_form_refuses_short_password():
    """Critère 3 : moins de 12 caractères, le mot de passe est refusé"""
    form = UserCreationForm(
        data={
            "email": "court@legrandcinema.test",
            "role": User.Role.BOX_OFFICE,
            "usable_password": "true",
            "password1": "Court-2026",
            "password2": "Court-2026",
        }
    )

    assert not form.is_valid()
    assert "password2" in form.errors


def test_programming_can_open_movies(client, make_user):
    """Critère 2 : la programmation gère les films dans l'admin"""
    client.force_login(make_user(User.Role.PROGRAMMING))

    response = client.get(reverse("admin:programme_movie_changelist"))

    assert response.status_code == 200


def test_programming_cannot_open_accounts(client, make_user):
    """Critère 2 : la programmation n'a pas accès aux comptes"""
    client.force_login(make_user(User.Role.PROGRAMMING))

    response = client.get(reverse("admin:accounts_user_changelist"))

    assert response.status_code == 403


def test_box_office_cannot_open_admin(client, make_user):
    """Critère 2 : l'agent d'accueil n'entre pas dans l'admin Django"""
    client.force_login(make_user(User.Role.BOX_OFFICE))

    response = client.get(reverse("admin:index"))

    # Redirection vers la page de connexion de l'admin
    assert response.status_code == 302


def test_admin_login_page_opens_for_anonymous_visitor(client):
    """Non-régression : la page de connexion de l'admin s'affiche

    Bug trouvé au test manuel : AttributeError 'AnonymousUser' object has
    no attribute 'role' (ProgrammationAdmin.has_role)
    """
    response = client.get(reverse("admin:login"))

    assert response.status_code == 200
