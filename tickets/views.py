"""Image du QR code d'un billet (US 4.1)"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from booking.models import Ticket
from tickets.services import qr_code_png


@require_GET
def ticket_qr(request, pk):
    """Renvoie l'image PNG du QR code d'un billet vendu

    L'identifiant du billet (UUID non devinable) sert de clé, comme pour
    la réservation ; un billet pas encore payé renvoie une 404
    """
    ticket = get_object_or_404(Ticket, pk=pk, status=Ticket.Status.SOLD)
    return HttpResponse(qr_code_png(ticket), content_type="image/png")
