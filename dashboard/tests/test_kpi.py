"""Tests des indicateurs du projet pour la direction (US 8.2)"""

from datetime import date, datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User
from booking.models import Booking, Ticket
from booking.services import hold_seats, sell_at_box_office
from dashboard.models import KpiSetting
from dashboard.services import project_kpi
from programme.models import Screening

pytestmark = pytest.mark.django_db

URL = "/api/dashboard/kpi/"

# Jour du calcul : dimanche 13 janvier 2030, 7e jour après le lancement
TODAY = date(2030, 1, 13)


def make_screening(movie, room, day, hour):
    """Séance de janvier 2030 (heure de Paris)"""
    starts_at = timezone.make_aware(datetime(2030, 1, day, hour, 0))
    return Screening.objects.create(
        movie=movie, room=room, starts_at=starts_at
    )


def pay_online(screening, seats, postcode="48000", country=""):
    """Réservation en ligne payée, avec le lieu de résidence (US 2.4)"""
    booking = hold_seats(screening, seats)
    booking.customer_email = "marine@example.com"
    booking.customer_postcode = postcode
    booking.customer_country = country
    booking.status = Booking.Status.CONFIRMED
    booking.save()
    booking.tickets.update(status=Ticket.Status.SOLD)


@pytest.fixture
def launch():
    """Réglage d'Isabelle : application lancée le lundi 7 janvier 2030"""
    return KpiSetting.objects.create(launch_date=date(2030, 1, 7))


@pytest.fixture
def sales(launch, movie, room, seats, price, make_user):
    """Ventes de la 1re semaine dans la salle de test (4 places)

    Lundi 7 à 14 h (ni soir ni week-end) : 2 places en ligne (habitant
    de Lozère) et 1 au guichet ; mardi 8 à 20 h (soir) : 1 place en
    ligne (touriste allemand) ; dimanche 20 (après le jour du calcul) :
    1 place en ligne, pas encore comptée
    """
    monday = make_screening(movie, room, 7, 14)
    tuesday = make_screening(movie, room, 8, 20)
    later = make_screening(movie, room, 20, 20)
    pay_online(monday, seats[:2])
    agent = make_user(User.Role.BOX_OFFICE)
    tickets = [{"seat": seats[2], "price": price}]
    sell_at_box_office(monday, tickets, Booking.PaymentMethod.CASH, agent)
    pay_online(tuesday, seats[:1], postcode="", country="DE")
    pay_online(later, seats[:1])


def test_attendance_compared_to_the_target_trajectory(sales):
    """Critère 1 : fréquentation cumulée et trajectoire cible"""
    kpi = project_kpi(TODAY)

    assert kpi["days"] == 7
    assert kpi["attendance"] == 4  # la séance du 20 n'a pas eu lieu
    # 527 280 entrées par an visées : 527 280 x 7 / 365
    assert kpi["target"] == 10112
    # Rythme d'avant l'application : 405 600 x 7 / 365
    assert kpi["baseline"] == 7779


def test_share_of_online_bookings(sales):
    """Critère 2 : part des réservations en ligne (cible 60 %)"""
    kpi = project_kpi(TODAY)

    assert kpi["online_share"] == 67  # 2 réservations sur 3
    assert kpi["online_target"] == 60


def test_fill_rate_at_peak_times(sales):
    """Critère 2 : remplissage en affluence (soir, week-end, festival)"""
    kpi = project_kpi(TODAY)

    # Seule la séance du mardi soir compte : 1 place sur 4
    assert kpi["peak_rate"] == 25
    assert kpi["peak_target"] == 80


def test_festival_screenings_count_as_peak(sales, launch):
    """Une séance pendant le festival est une séance d'affluence"""
    launch.festival_start = date(2030, 1, 7)
    launch.festival_end = date(2030, 1, 7)
    launch.save()

    kpi = project_kpi(TODAY)

    assert kpi["peak_rate"] == 50  # lundi (3 places) et mardi (1) sur 8


def test_share_of_tourists_during_the_festival(sales, launch):
    """Critère 2 : touristes (hors Lozère) pendant le festival"""
    launch.festival_start = date(2030, 1, 7)
    launch.festival_end = date(2030, 1, 8)
    launch.save()

    kpi = project_kpi(TODAY)

    # Réservations en ligne du festival : une de Lozère, une d'Allemagne
    assert kpi["tourist_share"] == 50
    assert kpi["tourist_target"] == 20


def test_no_tourist_share_without_festival_dates(sales):
    """Sans dates du festival, la part de touristes n'est pas calculée"""
    kpi = project_kpi(TODAY)

    assert kpi["tourist_share"] is None


def test_kpi_are_recalculated_at_each_reading(sales, movie, room, seats):
    """Critère 3 : indicateurs à jour à chaque consultation"""
    first = project_kpi(TODAY)
    saturday = make_screening(movie, room, 12, 14)
    pay_online(saturday, seats[:2])

    second = project_kpi(TODAY)

    assert second["attendance"] == first["attendance"] + 2


def test_management_reads_the_kpi(client, make_user):
    """Critère 1 : tableau des KPI ouvert au rôle direction"""
    client.force_login(make_user(User.Role.MANAGEMENT))

    response = client.get(URL)

    assert response.status_code == 200
    assert "attendance" in response.json()


def test_only_management_and_isabelle_read_the_kpi(client, make_user):
    """Indicateurs réservés à la direction et à Isabelle (US 9.1)"""
    assert client.get(URL).status_code == 401
    client.force_login(make_user(User.Role.BOX_OFFICE))
    assert client.get(URL).status_code == 403
    client.force_login(make_user(User.Role.ADMIN))
    assert client.get(URL).status_code == 200


def test_kpi_export_in_csv(client, make_user):
    """Critère 3 : indicateurs exportables en CSV"""
    client.force_login(make_user(User.Role.MANAGEMENT))

    response = client.get(URL + "csv/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    content = response.content.decode("utf-8-sig")
    assert content.startswith("Indicateur;Valeur;Cible")
    assert "Part des réservations en ligne (%)" in content


def test_festival_cannot_end_before_it_starts():
    """Réglage d'Isabelle : la fin du festival suit son début"""
    setting = KpiSetting(
        festival_start=date(2030, 1, 8), festival_end=date(2030, 1, 7)
    )

    with pytest.raises(ValidationError):
        setting.full_clean()
