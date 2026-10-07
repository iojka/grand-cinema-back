"""Règles métier de la réservation : blocage et libération des places

Fonctions appelées par les vues de l'API (US 2.2)
"""

from django.db import transaction
from django.utils import timezone

from booking.models import HOLD_DURATION, Booking, Ticket
from programme.models import Price


def release_expired_bookings() -> None:
    """Libère les places des réservations dont le blocage a expiré

    Appelée à chaque lecture du plan de salle et avant chaque blocage :
    une place bloquée depuis plus de 10 minutes redevient libre
    (critère 3 de l'US 2.2)
    """
    now = timezone.now()
    expired = Booking.objects.filter(
        status=Booking.Status.PENDING, expires_at__lt=now
    )
    Ticket.objects.filter(booking__in=expired).delete()
    expired.update(status=Booking.Status.EXPIRED)


@transaction.atomic
def hold_seats(screening, seats) -> Booking:
    """Bloque des places pendant 10 minutes, toutes ou aucune

    La contrainte d'unicité (séance, place) de la base refuse une place
    déjà prise, même si deux spectateurs la demandent au même moment
    (critère 4) ; la transaction annule alors tout le blocage

    :param screening: séance choisie
    :param seats: places côte à côte, déjà vérifiées
    :return: la réservation en attente de paiement
    :raises IntegrityError: si une des places est déjà prise
    """
    # Plein tarif (le plus cher) en attendant le choix du tarif (US 2.3)
    price = Price.objects.filter(is_active=True).first()
    unit_price = price.amount_for(screening.room)
    booking = Booking.objects.create(
        screening=screening,
        channel=Booking.Channel.WEB,
        expires_at=timezone.now() + HOLD_DURATION,
        total_amount=unit_price * len(seats),
    )
    for seat in seats:
        Ticket.objects.create(
            booking=booking,
            screening=screening,
            seat=seat,
            price=price,
            unit_price=unit_price,
        )
    return booking
