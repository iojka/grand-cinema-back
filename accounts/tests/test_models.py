"""Tests des comptes du back office (US 9.1)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Un-mot-de-passe-solide"


def test_create_user_uses_email_as_login_and_hashes_password():
    """Le login est l'e-mail et le mot de passe n'est jamais en clair."""
    user = User.objects.create_user(
        email="Agent@GrandCinema.fr", password=PASSWORD
    )

    assert user.email == "Agent@grandcinema.fr"  # domaine en minuscules
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)
    assert user.role == User.Role.BOX_OFFICE
    assert not user.is_staff


def test_email_must_be_unique():
    """Deux comptes ne peuvent pas avoir la même adresse e-mail."""
    User.objects.create_user(
        email="isabelle@grandcinema.fr", password=PASSWORD
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="isabelle@grandcinema.fr", password=PASSWORD
        )


def test_create_superuser_gets_admin_role():
    """Le compte créé par createsuperuser reçoit le rôle administrateur."""
    admin = User.objects.create_superuser(
        email="admin@grandcinema.fr", password=PASSWORD
    )

    assert admin.role == User.Role.ADMIN
    assert admin.is_staff
    assert admin.is_superuser


def test_password_shorter_than_12_characters_is_refused():
    """US 9.1 : un mot de passe de moins de 12 caractères est refusé."""
    with pytest.raises(ValidationError):
        validate_password("Court-2026")
