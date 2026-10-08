"""Paiement en ligne avec Stripe (US 3.1) et confirmation (US 3.3)

Le spectateur paie sur la page hébergée par Stripe (3D Secure compris) :
aucune donnée de carte ne passe par l'application. On ne garde que
l'identifiant de la session de paiement et celui des notifications
"""

import time

import stripe
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from booking.models import Booking, Ticket
from payment.models import StripeEvent

# Stripe impose au moins 30 minutes avant l'expiration d'une session
# de paiement (plus que nos 10 minutes de blocage : voir la D3 Q3)
SESSION_DURATION = 31 * 60  # en secondes

# Textes de l'e-mail de confirmation, en français et en anglais (US 3.3)
EMAILS = {
    "fr": {
        "subject": "Le Grand Cinéma : réservation {reference} confirmée",
        "body": (
            "Bonjour {name},\n\n"
            "Votre paiement est confirmé. Voici votre réservation.\n\n"
            "Numéro de réservation : {reference}\n"
            "Film : {movie}\n"
            "Date et heure : {date}\n"
            "Salle : {room}\n"
            "Places : {seats}\n"
            "Montant payé : {total} €\n\n"
            "Retrouvez votre réservation : {link}\n\n"
            "À bientôt au Grand Cinéma !"
        ),
    },
    "en": {
        "subject": "Le Grand Cinéma: booking {reference} confirmed",
        "body": (
            "Hello {name},\n\n"
            "Your payment is confirmed. Here is your booking.\n\n"
            "Booking number: {reference}\n"
            "Film: {movie}\n"
            "Date and time: {date}\n"
            "Screen: {room}\n"
            "Seats: {seats}\n"
            "Amount paid: €{total}\n\n"
            "See your booking: {link}\n\n"
            "See you soon at Le Grand Cinéma!"
        ),
    },
}


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
        # US 3.3 : e-mail seulement après un paiement confirmé
        # (critère 3). Dans la transaction : si l'envoi échoue, rien
        # n'est enregistré et Stripe renverra la notification
        send_confirmation(booking)


def send_confirmation(booking) -> None:
    """Envoie l'e-mail de confirmation dans la langue du spectateur

    :param booking: réservation confirmée par Stripe
    """
    text = EMAILS[booking.customer_language]
    seats = []
    for ticket in booking.tickets.all():
        seats.append(f"{ticket.seat.row}{ticket.seat.number}")
    total = str(booking.total_amount)
    if booking.customer_language == "fr":
        total = total.replace(".", ",")  # 22,00 € en français
    starts_at = timezone.localtime(booking.screening.starts_at)
    page = f"{settings.FRONT_URL}/reservation/{booking.pk}"
    values = {
        "name": booking.customer_name,
        "reference": booking.reference,
        "movie": booking.screening.movie.title,
        "date": starts_at.strftime("%d/%m/%Y %H:%M"),
        "room": booking.screening.room.name,
        "seats": ", ".join(seats),
        "total": total,
        "link": f"{page}/confirmation",
    }
    send_mail(
        text["subject"].format(**values),
        text["body"].format(**values),
        None,  # expéditeur : DEFAULT_FROM_EMAIL des réglages
        [booking.customer_email],
    )
