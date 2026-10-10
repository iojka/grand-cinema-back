"""Calculs des tableaux de bord du pilotage (EPIC 8)

Taux de remplissage = places vendues / capacité de la salle (US 8.1)
"""

from datetime import timedelta

from django.utils import timezone

from booking.models import Booking, Ticket
from programme.models import Room, Screening


def fill_rate(sold, capacity) -> int:
    """Calcule un taux de remplissage

    :param sold: places vendues
    :param capacity: capacité de la ou des salles
    :return: le taux en %, arrondi à l'unité (0 si aucune place)
    """
    if capacity == 0:
        return 0
    return round(sold * 100 / capacity)


def group_rates(lines, key) -> list:
    """Regroupe les séances par salle, par jour ou par semaine

    :param lines: séances avec leur capacité et leurs places vendues
    :param key: clé du regroupement ("room", "day" ou "week")
    :return: un groupe par valeur de la clé, trié, avec son taux
    """
    groups = {}
    for line in lines:
        label = line[key]
        if label not in groups:
            groups[label] = {"label": label, "capacity": 0, "sold": 0}
        groups[label]["capacity"] += line["capacity"]
        groups[label]["sold"] += line["sold"]
    result = []
    for label in sorted(groups):
        group = groups[label]
        group["fill_rate"] = fill_rate(group["sold"], group["capacity"])
        result.append(group)
    return result


def occupancy(start, end) -> dict:
    """Tableau de bord du remplissage d'une période (US 8.1)

    :param start: premier jour de la période
    :param end: dernier jour de la période
    :return: taux par séance, salle, jour et semaine, ventes web et
        guichet de la période
    """
    screenings = (
        Screening.objects.filter(
            starts_at__date__gte=start, starts_at__date__lte=end
        )
        .exclude(status=Screening.Status.CANCELLED)
        .select_related("movie", "room")
        .order_by("starts_at")
    )
    # Capacité de chaque salle (le cinéma n'a que quelques salles)
    capacities = {}
    for room in Room.objects.all():
        capacities[room.pk] = room.capacity
    # Places vendues de la période, lues en une seule requête :
    # {id de la séance: nombre de places}
    web = {}
    box_office = {}
    tickets = Ticket.objects.filter(
        screening__in=screenings, status=Ticket.Status.SOLD
    ).values("screening_id", "booking__channel")
    for ticket in tickets:
        screening_id = ticket["screening_id"]
        if ticket["booking__channel"] == Booking.Channel.WEB:
            web[screening_id] = web.get(screening_id, 0) + 1
        else:
            box_office[screening_id] = box_office.get(screening_id, 0) + 1
    lines = []
    for screening in screenings:
        starts_at = timezone.localtime(screening.starts_at)
        day = starts_at.date()
        # Une semaine est désignée par son lundi
        monday = day - timedelta(days=day.weekday())
        capacity = capacities[screening.room_id]
        sold = web.get(screening.pk, 0) + box_office.get(screening.pk, 0)
        lines.append(
            {
                "id": screening.pk,
                "starts_at": starts_at.isoformat(),
                "movie": screening.movie.title,
                "room": screening.room.name,
                "day": day.isoformat(),
                "week": monday.isoformat(),
                "capacity": capacity,
                "sold": sold,
                "fill_rate": fill_rate(sold, capacity),
            }
        )
    return {
        "screenings": lines,
        "rooms": group_rates(lines, "room"),
        "days": group_rates(lines, "day"),
        "weeks": group_rates(lines, "week"),
        "web": sum(web.values()),
        "box_office": sum(box_office.values()),
    }
