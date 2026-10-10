"""Tests de la connexion du personnel par l'API (US 9.1, jeton JWT)"""

import logging

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/auth/login/"
ME_URL = "/api/auth/me/"


def login(client, email, password):
    """Envoie une demande de connexion à l'API

    :return: la réponse de l'API
    """
    return client.post(
        LOGIN_URL,
        {"email": email, "password": password},
        content_type="application/json",
    )


def test_login_returns_a_token_with_the_role(client, make_user, password):
    """Une connexion réussie renvoie un jeton qui contient le rôle"""
    agent = make_user(User.Role.BOX_OFFICE)

    response = login(client, agent.email, password)

    assert response.status_code == 200
    token = AccessToken(response.json()["access"])
    assert token["role"] == User.Role.BOX_OFFICE


def test_login_with_wrong_password_is_refused(client, make_user):
    """Un mauvais mot de passe est refusé (401)"""
    agent = make_user(User.Role.BOX_OFFICE)

    response = login(client, agent.email, "Mauvais-mot-de-passe")

    assert response.status_code == 401


def test_account_is_locked_after_5_failures(client, make_user, password):
    """Critère 4 : après 5 échecs, même le bon mot de passe est refusé"""
    agent = make_user(User.Role.BOX_OFFICE)
    for _ in range(5):
        login(client, agent.email, "Mauvais-mot-de-passe")

    response = login(client, agent.email, password)

    assert response.status_code == 401
    agent.refresh_from_db()
    assert agent.is_locked()


def test_success_resets_failure_counter(client, make_user, password):
    """Des échecs non consécutifs ne verrouillent pas le compte"""
    agent = make_user(User.Role.BOX_OFFICE)
    for _ in range(4):
        login(client, agent.email, "Mauvais-mot-de-passe")

    login(client, agent.email, password)

    agent.refresh_from_db()
    assert agent.failed_attempts == 0
    assert not agent.is_locked()


def test_disabled_account_is_refused(client, make_user, password, caplog):
    """Critère 5 : un compte désactivé est refusé et c'est journalisé"""
    agent = make_user(User.Role.BOX_OFFICE, is_active=False)

    response = login(client, agent.email, password)

    assert response.status_code == 401
    assert "compte désactivé" in caplog.text


def test_disabled_account_token_stops_working(client, make_user, password):
    """Critère 5 : un compte désactivé perd l'accès immédiatement"""
    agent = make_user(User.Role.BOX_OFFICE)
    token = login(client, agent.email, password).json()["access"]
    agent.is_active = False
    agent.save()

    response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 401


def test_successful_login_is_logged(client, make_user, password, caplog):
    """Les connexions réussies sont journalisées"""
    agent = make_user(User.Role.BOX_OFFICE)
    caplog.set_level(logging.INFO, logger="accounts")

    login(client, agent.email, password)

    assert "Connexion réussie" in caplog.text


def test_me_requires_a_token(client):
    """Sans jeton, le compte connecté n'est pas accessible (401)"""
    response = client.get(ME_URL)

    assert response.status_code == 401


def test_me_returns_the_connected_account(client, make_user, password):
    """Avec un jeton, l'API renvoie l'e-mail et le rôle du compte"""
    agent = make_user(User.Role.BOX_OFFICE)
    token = login(client, agent.email, password).json()["access"]

    response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {token}")

    assert response.status_code == 200
    assert response.json()["role"] == User.Role.BOX_OFFICE
