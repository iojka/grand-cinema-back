"""Calculs des tableaux de bord du pilotage (EPIC 8)

Taux de remplissage = places vendues / capacité de la salle (US 8.1),
indicateurs du projet pour la direction (US 8.2), alerte à Isabelle
quand une séance franchit le seuil (US 8.3)
"""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from booking.models import Booking, Ticket
from dashboard.models import (
    DEFAULT_THRESHOLD,
    AlertSetting,
    KpiSetting,
    OccupancyAlert,
)
from programme.models import Room, Screening

# Trajectoire du Bloc 1 : entrées par an avant l'application et visées
BASELINE_PER_YEAR = 405600
TARGET_PER_YEAR = 527280
# Cibles du Bloc 1, en %
ONLINE_TARGET = 60
PEAK_TARGET = 80
TOURIST_TARGET = 20
# Une séance du soir commence à 18 h ou plus tard
EVENING_HOUR = 18


def percent(part, total) -> int:
    """Calcule un pourcentage

    :param part: nombre compté
    :param total: nombre total
    :return: le pourcentage arrondi à l'unité (0 si le total est nul)
    """
    if total == 0:
        return 0
    return round(part * 100 / total)


def fill_rate(sold, capacity) -> int:
    """Calcule un taux de remplissage

    :param sold: places vendues
    :param capacity: capacité de la ou des salles
    :return: le taux en %, arrondi à l'unité (0 si aucune place)
    """
    return percent(sold, capacity)


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


def room_capacities() -> dict:
    """Capacité de chaque salle (le cinéma n'a que quelques salles)

    :return: {id de la salle: nombre de places}
    """
    capacities = {}
    for room in Room.objects.all():
        capacities[room.pk] = room.capacity
    return capacities


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
    capacities = room_capacities()
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


def kpi_setting():
    """Réglage des indicateurs fait par Isabelle dans l'admin (US 8.2)

    :return: le réglage, ou un réglage par défaut (non enregistré)
    """
    setting = KpiSetting.objects.first()
    if setting is None:
        return KpiSetting()
    return setting


def in_festival(day, setting) -> bool:
    """Vérifie qu'un jour fait partie du festival

    :param day: jour à vérifier
    :param setting: réglage des indicateurs
    :return: False si les dates du festival ne sont pas réglées
    """
    if setting.festival_start is None or setting.festival_end is None:
        return False
    return setting.festival_start <= day <= setting.festival_end


def is_peak(screening, setting) -> bool:
    """Séance d'affluence : soir, week-end ou festival (Bloc 1)

    :param screening: séance à vérifier
    :param setting: réglage des indicateurs
    """
    starts_at = timezone.localtime(screening.starts_at)
    # weekday() : 5 pour samedi, 6 pour dimanche
    if starts_at.hour >= EVENING_HOUR or starts_at.weekday() >= 5:
        return True
    return in_festival(starts_at.date(), setting)


def is_tourist(booking) -> bool:
    """Spectateur qui n'habite pas en Lozère (code postal 48...)

    :param booking: réservation en ligne (US 2.4 : code postal ou pays)
    """
    if booking.customer_country not in ("", "FR"):
        return True
    return not booking.customer_postcode.startswith("48")


def project_kpi(today) -> dict:
    """Indicateurs du projet pour la direction (US 8.2)

    Recalculés à chaque consultation, du lancement jusqu'au jour donné

    :param today: jour du calcul
    :return: valeur de chaque indicateur et sa cible
    """
    setting = kpi_setting()
    # Jours écoulés depuis le lancement, jour du lancement compris
    days = max((today - setting.launch_date).days + 1, 0)
    screenings = Screening.objects.filter(
        starts_at__date__gte=setting.launch_date,
        starts_at__date__lte=today,
    ).exclude(status=Screening.Status.CANCELLED)
    # Places vendues par séance, lues en une seule requête
    sold = {}
    tickets = Ticket.objects.filter(
        screening__in=screenings, status=Ticket.Status.SOLD
    ).values("screening_id")
    for ticket in tickets:
        screening_id = ticket["screening_id"]
        sold[screening_id] = sold.get(screening_id, 0) + 1
    attendance = sum(sold.values())
    # Remplissage des séances d'affluence
    capacities = room_capacities()
    peak_capacity = 0
    peak_sold = 0
    for screening in screenings:
        if is_peak(screening, setting):
            peak_capacity += capacities[screening.room_id]
            peak_sold += sold.get(screening.pk, 0)
    # Réservations payées, en ligne et au guichet
    bookings = Booking.objects.filter(
        screening__in=screenings, status=Booking.Status.CONFIRMED
    ).select_related("screening")
    total = 0
    online = []
    for booking in bookings:
        total += 1
        if booking.channel == Booking.Channel.WEB:
            online.append(booking)
    # Touristes : réservations en ligne des séances du festival (le
    # guichet ne demande pas le lieu de résidence)
    tourist_share = None
    if setting.festival_start and setting.festival_end:
        festival = 0
        tourists = 0
        for booking in online:
            day = timezone.localdate(booking.screening.starts_at)
            if in_festival(day, setting):
                festival += 1
                if is_tourist(booking):
                    tourists += 1
        tourist_share = percent(tourists, festival)
    target = round(TARGET_PER_YEAR * days / 365)
    return {
        "today": today.isoformat(),
        "launch_date": setting.launch_date.isoformat(),
        "days": days,
        "attendance": attendance,
        "target": target,
        "baseline": round(BASELINE_PER_YEAR * days / 365),
        "progress": percent(attendance, target),
        "online_share": percent(len(online), total),
        "online_target": ONLINE_TARGET,
        "peak_rate": percent(peak_sold, peak_capacity),
        "peak_target": PEAK_TARGET,
        "tourist_share": tourist_share,
        "tourist_target": TOURIST_TARGET,
    }


def alert_threshold() -> int:
    """Seuil d'alerte réglé par Isabelle dans l'admin (US 8.3)

    :return: le seuil en %, 80 si rien n'a été réglé
    """
    setting = AlertSetting.objects.first()
    if setting is None:
        return DEFAULT_THRESHOLD
    return setting.threshold


def check_occupancy(screening) -> None:
    """Alerte Isabelle si la séance franchit le seuil (US 8.3)

    Appelée après chaque vente (guichet et paiement en ligne)

    :param screening: séance qui vient d'être vendue
    """
    sold = screening.tickets.filter(status=Ticket.Status.SOLD).count()
    rate = fill_rate(sold, screening.room.capacity)
    threshold = alert_threshold()
    if rate < threshold:
        return
    # Une seule alerte par séance (critère 2) : get_or_create ne crée
    # l'alerte que si elle n'existe pas déjà
    alert, created = OccupancyAlert.objects.get_or_create(
        screening=screening, defaults={"fill_rate": rate}
    )
    if created:
        send_alert(alert, threshold)


def send_alert(alert, threshold) -> None:
    """Envoie l'alerte par e-mail aux comptes administrateurs

    :param alert: alerte qui vient d'être créée
    :param threshold: seuil d'alerte franchi, en %
    """
    screening = alert.screening
    starts_at = timezone.localtime(screening.starts_at)
    # Critère 3 : lien direct vers la séance dans le back office
    link = settings.BACK_OFFICE_URL + reverse(
        "admin:programme_screening_change", args=[screening.pk]
    )
    subject = (
        f"Alerte remplissage : {screening.movie.title} "
        f"le {starts_at:%d/%m} à {alert.fill_rate} %"
    )
    message = (
        "Bonjour,\n\n"
        f"La séance « {screening.movie.title} » du "
        f"{starts_at:%d/%m/%Y} à {starts_at:%H:%M} ({screening.room.name}) "
        "est "
        f"remplie à {alert.fill_rate} % (seuil d'alerte : {threshold} %).\n"
        "Pour anticiper le pic, vous pouvez basculer la séance dans une "
        "salle plus grande ou ajouter une séance :\n"
        f"{link}\n\n"
        "Le Grand Cinéma"
    )
    recipients = []
    for user in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        recipients.append(user.email)
    send_mail(subject, message, None, recipients)
