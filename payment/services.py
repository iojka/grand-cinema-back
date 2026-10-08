"""Paiement en ligne avec Stripe (US 3.1)

Le spectateur paie sur la page hébergée par Stripe (3D Secure compris) :
aucune donnée de carte ne passe par l'application. On ne garde que
l'identifiant de la session de paiement et celui des notifications
"""

import time

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from booking.models import Booking, Ticket
from payment.models import StripeEvent

# Stripe impose au moins 30 minutes avant l'expiration d'une session
# de paiement (plus que nos 10 minutes de blocage : voir la D3 Q3)
SESSION_DURATION = 31 * 60  # en secondes


def create_checkout_session(booking) -> str:
    """Crée la page de paiement Stripe du panier

    :param booking: panier en attente, avec les coordonnées (US 2.4)
    :return: l'adresse de la page de paiement Stripe
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    title = booking.screening.movie.title
    # Une ligne par place, prix en centimes
    lines = []
    for ticket in booking.tickets.all():
        seat = f"{ticket.seat.row}{ticket.seat.number}"
        lines.append(
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": f"{title} - place {seat}"},
                    "unit_amount": int(ticket.unit_price * 100),
                },
                "quantity": 1,
            }
        )
    page = f"{settings.FRONT_URL}/reservation/{booking.pk}"
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=lines,
        customer_email=booking.customer_email,
        client_reference_id=str(booking.pk),
        success_url=f"{page}/confirmation",
        cancel_url=f"{page}?paiement=annule",
        expires_at=int(time.time()) + SESSION_DURATION,
    )
    booking.stripe_session_id = session.id
    booking.save()
    return session.url


@transaction.atomic
def confirm_payment(event) -> None:
    """Confirme la réservation payée, une seule fois par notification

    :param event: notification « checkout.session.completed » vérifiée
    """
    # Stripe peut envoyer plusieurs fois la même notification (critère 4)
    if StripeEvent.objects.filter(event_id=event["id"]).exists():
        return
    session = event["data"]["object"]
    booking = Booking.objects.filter(stripe_session_id=session["id"]).first()
    StripeEvent.objects.create(
        event_id=event["id"], event_type=event["type"], booking=booking
    )
    if booking is None or session["payment_status"] != "paid":
        return
    if booking.status == Booking.Status.PENDING:
        booking.status = Booking.Status.CONFIRMED
        booking.payment_method = Booking.PaymentMethod.ONLINE_CARD
        booking.confirmed_at = timezone.now()
        booking.save()
        booking.tickets.update(status=Ticket.Status.SOLD)
