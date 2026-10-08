"""Billets : image du QR code (US 4.1) et PDF à imprimer (US 4.2)"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from booking.models import Booking, Ticket
from tickets.services import qr_code_png, tickets_pdf


@require_GET
def ticket_qr(request, pk):
    """Renvoie l'image PNG du QR code d'un billet vendu

    L'identifiant du billet (UUID non devinable) sert de clé, comme pour
    la réservation ; un billet pas encore payé renvoie une 404
    """
    ticket = get_object_or_404(Ticket, pk=pk, status=Ticket.Status.SOLD)
    return HttpResponse(qr_code_png(ticket), content_type="image/png")


@require_GET
def download_pdf(request, pk):
    """Télécharge les billets à imprimer d'une réservation confirmée

    Le lien de l'e-mail mène à la page de confirmation, qui propose ce
    téléchargement autant de fois que nécessaire (US 4.2, critère 3)
    """
    booking = get_object_or_404(
        Booking, pk=pk, status=Booking.Status.CONFIRMED
    )
    response = HttpResponse(
        tickets_pdf(booking), content_type="application/pdf"
    )
    filename = f"billets-{booking.reference}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
