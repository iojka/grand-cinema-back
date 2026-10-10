"""Billets : image du QR code (US 4.1), PDF à imprimer (US 4.2) et
contrôle à l'entrée (US 7.3)
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasRole
from booking.models import Booking, Ticket
from tickets.serializers import (
    EntrySerializer,
    ScannedTicketSerializer,
    ScanResultSerializer,
    ScanSerializer,
)
from tickets.services import (
    check_in,
    check_ticket,
    qr_code_png,
    screening_entries,
    tickets_pdf,
)

# Le contrôle à l'entrée est fait par le personnel de l'accueil (US 9.1)
STAFF_ROLES = [User.Role.BOX_OFFICE, User.Role.ADMIN]


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


class ScanView(APIView):
    """Scan d'un billet QR code à l'entrée de la salle (US 7.3)"""

    permission_classes = [HasRole]
    allowed_roles = STAFF_ROLES

    @extend_schema(
        summary="Contrôler un billet à l'entrée",
        tags=["Contrôle"],
        request=ScanSerializer,
        responses=ScanResultSerializer,
    )
    def post(self, request):
        serializer = ScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result, ticket = check_ticket(
            serializer.validated_data["screening"],
            serializer.validated_data["code"],
            request.user,
        )
        data = None
        if ticket is not None:
            data = ScannedTicketSerializer(ticket).data
        return Response({"result": result, "ticket": data})


@extend_schema(summary="Liste des entrées d'une séance", tags=["Contrôle"])
class EntriesView(ListAPIView):
    """Réservations confirmées de la séance, chargées par la tablette
    pour le mode dégradé (critère 4)
    """

    serializer_class = EntrySerializer
    permission_classes = [HasRole]
    allowed_roles = STAFF_ROLES
    pagination_class = None  # toute la séance en une seule réponse

    def get_queryset(self):
        return screening_entries().filter(screening_id=self.kwargs["pk"])


class CheckInView(APIView):
    """Validation de l'entrée par le numéro de réservation (critère 4)"""

    permission_classes = [HasRole]
    allowed_roles = STAFF_ROLES

    @extend_schema(
        summary="Valider l'entrée d'une réservation",
        tags=["Contrôle"],
        request=None,
        responses=EntrySerializer,
    )
    def post(self, request, pk):
        booking = get_object_or_404(screening_entries(), pk=pk)
        check_in(booking, request.user)
        # Relecture : heure du 1er passage à jour
        booking = screening_entries().get(pk=pk)
        return Response(EntrySerializer(booking).data)
