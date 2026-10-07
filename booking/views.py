"""API publique du plan de salle (US 2.1)"""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from booking.serializers import SeatMapSerializer
from programme.models import next_screenings


@extend_schema(summary="Plan de salle d'une séance", tags=["Réservation"])
class SeatMapView(RetrieveAPIView):
    """Places libres, bloquées et vendues d'une séance à venir

    Route publique ; une séance passée, annulée ou inconnue renvoie une
    erreur 404. Le front relit cette route toutes les 4 secondes
    """

    serializer_class = SeatMapSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Seules les séances du programme (7 prochains jours) sont
        # réservables
        return next_screenings()
