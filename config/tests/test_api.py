"""Tests du socle de l'API"""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_ok(client):
    """La route de santé répond sans être connecté"""
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_schema_openapi(client):
    """Le schéma OpenAPI est généré et contient la route de santé"""
    response = client.get(reverse("schema"), {"format": "json"})

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "API Le Grand Cinéma"
    assert "/api/health/" in response.json()["paths"]


def test_swagger_accessible(client):
    """La page Swagger s'affiche"""
    response = client.get(reverse("swagger-ui"))

    assert response.status_code == 200


def test_cors_front_autorise(client):
    """Le front local a le droit d'appeler l'API"""
    origine = "http://localhost:5173"
    response = client.get(reverse("health"), HTTP_ORIGIN=origine)

    assert response.headers["Access-Control-Allow-Origin"] == origine


def test_cors_site_inconnu_refuse(client):
    """Un autre site n'a pas l'autorisation CORS"""
    response = client.get(
        reverse("health"), HTTP_ORIGIN="https://site-inconnu.example"
    )

    assert "Access-Control-Allow-Origin" not in response.headers
