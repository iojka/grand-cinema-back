"""Billet QR code (US 4.1) et billets PDF à imprimer (US 4.2)

Le QR code ne contient que l'identifiant du billet, signé avec la clé
secrète du serveur (SECRET_KEY, principe HMAC du cours sur les jetons) :
aucune donnée personnelle, et un faux billet sera repéré au scan (US 7.3)
"""

from io import BytesIO

import qrcode
from django.core.signing import Signer
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

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
