"""Billet QR code (US 4.1), billets PDF à imprimer (US 4.2) et contrôle
des billets à l'entrée (US 7.3)

Le QR code ne contient que l'identifiant du billet, signé avec la clé
secrète du serveur (SECRET_KEY, principe HMAC du cours sur les jetons) :
aucune donnée personnelle, et un faux billet sera repéré au scan (US 7.3)
"""

from io import BytesIO

import qrcode
from django.core.signing import BadSignature, Signer
from django.db.models import Min
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from booking.models import Booking, Ticket

# Résultats du scan : écran vert, rouge ou orange (US 7.3)
VALID = "VALID"
ALREADY_SCANNED = "ALREADY_SCANNED"
OTHER_SCREENING = "OTHER_SCREENING"
INVALID = "INVALID"

# Textes du billet PDF, en français et en anglais (US 4.2)
PDF_TEXTS = {
    "fr": {
        "title": "Le Grand Cinéma - Billet",
        "date": "Date et heure : ",
        "room": "Salle : ",
        "seat": "Place : ",
        "reference": "Réservation : ",
        "show": "Présentez ce billet à l'entrée de la salle.",
    },
    "en": {
        "title": "Le Grand Cinéma - Ticket",
        "date": "Date and time: ",
        "room": "Screen: ",
        "seat": "Seat: ",
        "reference": "Booking: ",
        "show": "Show this ticket at the entrance.",
    },
}


def ticket_token(ticket) -> str:
    """Contenu du QR code : l'identifiant du billet signé

    Le « sel » tickets réserve cette signature aux billets

    :param ticket: billet vendu
    :return: une chaîne « identifiant:signature »
    """
    return Signer(salt="tickets").sign(str(ticket.pk))


def qr_code_png(ticket) -> bytes:
    """Dessine le QR code du billet

    :param ticket: billet vendu
    :return: l'image PNG du QR code
    """
    image = qrcode.make(ticket_token(ticket))
    buffer = BytesIO()  # fichier en mémoire
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def tickets_pdf(booking) -> bytes:
    """Billets à imprimer : une page A4 par place, en noir et blanc

    :param booking: réservation confirmée
    :return: le document PDF
    """
    text = PDF_TEXTS[booking.customer_language]
    screening = booking.screening
    starts_at = timezone.localtime(screening.starts_at)
    buffer = BytesIO()  # fichier en mémoire
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for ticket in booking.tickets.all():
        seat = f"{ticket.seat.row}{ticket.seat.number}"
        # Texte noir, du haut vers le bas (l'origine est en bas à gauche)
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawString(2 * cm, 27 * cm, text["title"])
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(2 * cm, 25 * cm, screening.movie.title)
        pdf.setFont("Helvetica", 14)
        lines = [
            text["date"] + starts_at.strftime("%d/%m/%Y %H:%M"),
            text["room"] + screening.room.name,
            text["seat"] + seat,
            text["reference"] + booking.reference,
        ]
        y = 23.5 * cm
        for line in lines:
            pdf.drawString(2 * cm, y, line)
            y = y - 1 * cm
        # Même QR code que sur le téléphone (critère 2)
        image = ImageReader(BytesIO(qr_code_png(ticket)))
        pdf.drawImage(image, 2 * cm, 9 * cm, width=9 * cm, height=9 * cm)
        pdf.setFont("Helvetica", 12)
        pdf.drawString(2 * cm, 8 * cm, text["show"])
        pdf.showPage()  # page suivante
    pdf.save()
    return buffer.getvalue()


def check_ticket(screening, code, agent):
    """Contrôle un billet scanné à l'entrée de la salle (US 7.3)

    La signature prouve que le QR code a été fabriqué par le serveur
    (US 4.1) : un faux billet est refusé

    :param screening: séance contrôlée par l'agent
    :param code: texte lu dans le QR code (« identifiant:signature »)
    :param agent: agent d'accueil qui scanne
    :return: le résultat et le billet (None si le billet est invalide)
    """
    try:
        ticket_id = Signer(salt="tickets").unsign(code)
    except BadSignature:
        return INVALID, None
    ticket = Ticket.objects.filter(
        pk=ticket_id, status=Ticket.Status.SOLD
    ).first()
    if ticket is None:
        return INVALID, None
    if ticket.screening_id != screening.pk:
        return OTHER_SCREENING, ticket
    # Mise à jour seulement si le billet n'est pas encore passé : deux
    # scans au même moment ne valident qu'une seule entrée
    updated = Ticket.objects.filter(
        pk=ticket.pk, scanned_at__isnull=True
    ).update(scanned_at=timezone.now(), scanned_by=agent)
    ticket.refresh_from_db()
    if updated == 0:
        return ALREADY_SCANNED, ticket
    return VALID, ticket


def screening_entries():
    """Réservations confirmées avec l'heure du 1er passage (mode dégradé)

    :return: les réservations, avec scanned_at = heure du 1er billet
        scanné (None si personne n'est encore entré)
    """
    return (
        Booking.objects.filter(status=Booking.Status.CONFIRMED)
        .annotate(scanned_at=Min("tickets__scanned_at"))
        .prefetch_related("tickets__seat")
    )


def check_in(booking, agent) -> None:
    """Valide l'entrée d'une réservation par son numéro (US 7.3, critère 4)

    Les billets déjà passés gardent l'heure du 1er passage

    :param booking: réservation confirmée
    :param agent: agent d'accueil qui valide l'entrée
    """
    booking.tickets.filter(scanned_at__isnull=True).update(
        scanned_at=timezone.now(), scanned_by=agent
    )
