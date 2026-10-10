"""Tests de l'alerte de remplissage envoyée à Isabelle (US 8.3)"""

from unittest.mock import patch

import pytest
from django.core import mail

from accounts.models import User
from booking.models import Booking
from booking.services import hold_seats, sell_at_box_office
from dashboard.models import AlertSetting, OccupancyAlert
from dashboard.services import check_occupancy

pytestmark = pytest.mark.django_db

CONSTRUCT_EVENT = "payment.views.stripe.Webhook.construct_event"


@pytest.fixture
def isabelle(make_user):
    """Isabelle, administratrice : elle reçoit les alertes"""
    return make_user(User.Role.ADMIN, email="isabelle@legrandcinema.test")


@pytest.fixture
def agent(make_user):
    """Agent d'accueil qui vend au guichet"""
    return make_user(User.Role.BOX_OFFICE)


def sell(screening, seats, price, agent):
    """Vente de places au guichet (US 7.2), sans passer par l'API"""
    tickets = [{"seat": seat, "price": price} for seat in seats]
    sell_at_box_office(screening, tickets, Booking.PaymentMethod.CASH, agent)


def test_alert_at_the_default_threshold_of_80(
    isabelle, agent, screening, seats, price
):
    """Critère 1 : seuil de 80 % par défaut, e-mail envoyé à Isabelle"""
    sell(screening, seats[:3], price, agent)  # 3 places sur 4 : 75 %
    check_occupancy(screening)
    assert len(mail.outbox) == 0

    sell(screening, seats[3:], price, agent)  # 4 places sur 4 : 100 %
    check_occupancy(screening)

    assert OccupancyAlert.objects.get(screening=screening).fill_rate == 100
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["isabelle@legrandcinema.test"]
    assert "Film test" in mail.outbox[0].subject


def test_threshold_is_set_in_the_back_office(
    isabelle, agent, screening, seats, price
):
    """Critère 1 : seuil paramétrable par Isabelle"""
    AlertSetting.objects.create(threshold=50)

    sell(screening, seats[:2], price, agent)  # 2 places sur 4 : 50 %
    check_occupancy(screening)

    assert len(mail.outbox) == 1


def test_only_one_alert_per_screening(
    isabelle, agent, screening, seats, price
):
    """Critère 2 : pas de nouvelle alerte quand le remplissage augmente"""
    AlertSetting.objects.create(threshold=50)
    sell(screening, seats[:2], price, agent)  # 50 % : alerte
    check_occupancy(screening)

    sell(screening, seats[2:], price, agent)  # 100 % : pas de 2e alerte
    check_occupancy(screening)

    assert OccupancyAlert.objects.count() == 1
    assert len(mail.outbox) == 1


def test_alert_link_opens_the_screening(
    isabelle, agent, screening, seats, price
):
    """Critère 3 : le lien ouvre la séance dans le back office"""
    sell(screening, seats, price, agent)

    check_occupancy(screening)

    link = f"/admin/programme/screening/{screening.pk}/change/"
    assert link in mail.outbox[0].body


def test_box_office_sale_sends_the_alert(
    client, isabelle, agent, screening, seats, price
):
    """La vente au guichet qui franchit le seuil déclenche l'alerte"""
    client.force_login(agent)
    data = {
        "screening": screening.pk,
        "tickets": [{"seat": seat.pk, "price": price.pk} for seat in seats],
        "payment_method": "CASH",
    }

    client.post(
        "/api/booking/box-office/sales/", data, content_type="application/json"
    )

    assert OccupancyAlert.objects.filter(screening=screening).exists()


def test_online_payment_sends_the_alert(
    client, isabelle, screening, seats, price
):
    """Le paiement en ligne qui franchit le seuil déclenche l'alerte"""
    booking = hold_seats(screening, seats)
    booking.customer_email = "marine@example.com"
    booking.stripe_session_id = "cs_test_full"
    booking.save()
    event = {
        "id": "evt_test_full",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_full",
                "payment_status": "paid",
                "payment_intent": "pi_test_full",
            }
        },
    }

    with patch(CONSTRUCT_EVENT, return_value=event):
        client.post(
            "/api/payment/webhook/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=signature",
        )

    assert OccupancyAlert.objects.filter(screening=screening).exists()


def test_banner_in_the_back_office(
    client, isabelle, agent, screening, seats, price
):
    """Critères 1 et 3 : bandeau dans l'admin, avec le lien de la séance"""
    sell(screening, seats, price, agent)
    check_occupancy(screening)
    client.force_login(isabelle)

    content = client.get("/admin/").content.decode()

    assert "Alerte remplissage" in content
    assert f"/admin/programme/screening/{screening.pk}/change/" in content


def test_no_banner_without_alert(client, isabelle):
    """Pas de bandeau quand aucune séance n'a franchi le seuil"""
    client.force_login(isabelle)

    content = client.get("/admin/").content.decode()

    assert "Alerte remplissage" not in content
