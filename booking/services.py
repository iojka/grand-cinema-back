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


@transaction.atomic
def change_ticket_price(ticket, price) -> Booking:
    """Applique un tarif à une place puis recalcule le total (US 2.3)

    :param ticket: place du panier
    :param price: tarif choisi, déjà vérifié (actif)
    :return: la réservation avec son nouveau total
    """
    ticket.price = price
    ticket.unit_price = price.amount_for(ticket.screening.room)
    ticket.save()
    booking = ticket.booking
    total = 0
    for item in booking.tickets.all():
        total += item.unit_price
    booking.total_amount = total
    booking.save()
    return booking


@transaction.atomic
def cancel_booking(booking) -> None:
    """Annule un panier en attente : ses places redeviennent libres

    Utilisée quand le spectateur veut changer de places (US 2.3)

    :param booking: réservation en attente de paiement
    """
    booking.tickets.all().delete()
    booking.status = Booking.Status.CANCELLED
    booking.save()


@transaction.atomic
def sell_at_box_office(screening, tickets, payment_method, agent) -> Booking:
    """Vend des places au guichet sur le stock unique de places (US 7.2)

    Même contrainte d'unicité qu'en ligne : une place déjà bloquée ou
    vendue est refusée par la base, même au même moment (critère 2) ;
    la transaction annule alors toute la vente

    :param screening: séance choisie
    :param tickets: liste de {"seat": place, "price": tarif}
    :param payment_method: espèces ou carte via le terminal
    :param agent: agent d'accueil qui encaisse
    :return: la réservation confirmée
    :raises IntegrityError: si une des places est déjà prise
    """
    booking = Booking.objects.create(
        screening=screening,
        channel=Booking.Channel.BOX_OFFICE,
        status=Booking.Status.CONFIRMED,
        payment_method=payment_method,
        sold_by=agent,
        confirmed_at=timezone.now(),
    )
    total = 0
    for item in tickets:
        # Même calcul du prix que sur le site (critère 3)
        unit_price = item["price"].amount_for(screening.room)
        Ticket.objects.create(
            booking=booking,
            screening=screening,
            seat=item["seat"],
            price=item["price"],
            unit_price=unit_price,
            status=Ticket.Status.SOLD,
        )
        total += unit_price
    booking.total_amount = total
    booking.save()
    return booking
