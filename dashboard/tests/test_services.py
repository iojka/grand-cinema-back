"""Tests des calculs du tableau de bord (US 8.1)"""

from dashboard.services import fill_rate, group_rates


def test_fill_rate_is_a_rounded_percentage():
    """Places vendues sur capacité, en %, arrondi à l'unité"""
    assert fill_rate(3, 4) == 75
    assert fill_rate(1, 3) == 33


def test_fill_rate_of_an_empty_room_is_zero():
    """Une salle sans place ne provoque pas de division par zéro"""
    assert fill_rate(0, 0) == 0


def test_group_rates_adds_sold_seats_and_capacities():
    """Taux d'un groupe = total vendu / total des capacités"""
    lines = [
        {"room": "Salle 1", "capacity": 100, "sold": 90},
        {"room": "Salle 1", "capacity": 100, "sold": 10},
        {"room": "Salle 3", "capacity": 50, "sold": 5},
    ]

    groups = group_rates(lines, "room")

    assert groups == [
        {"label": "Salle 1", "capacity": 200, "sold": 100, "fill_rate": 50},
        {"label": "Salle 3", "capacity": 50, "sold": 5, "fill_rate": 10},
    ]
