"""API publique du plan de salle et du blocage des places (US 2.1 et 2.2)"""

from django.db import IntegrityError
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from booking.serializers import (
    BookingHoldSerializer,
    HoldSerializer,
    SeatMapSerializer,
)
from booking.services import hold_seats, release_expired_bookings
from programme.models import next_screenings

# Message affiché au spectateur si une place vient d'être prise (critère 2)
SEAT_TAKEN = (
    "Une des places vient d'être prise. Le plan a été mis à jour, "
    "choisissez d'autres places."
)


@extend_schema(summary="Plan de salle d'une séance", tags=["Réservation"])
class SeatMapView(RetrieveAPIView):
    """Places libres, bloquées et vendues d'une séance à venir

    Route publique ; une séance passée, annulée ou inconnue renvoie une
    erreur 404. Le front relit cette route toutes les 4 secondes
    """

    serializer_class = SeatMapSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Les blocages expirés sont libérés avant l'affichage (US 2.2)
        release_expired_bookings()
        # Seules les séances du programme (7 prochains jours) sont
        # réservables
        return next_screenings()


class HoldView(APIView):
    """Bloque des places côte à côte pendant 10 minutes (US 2.2)

    Route publique : le spectateur réserve sans compte (US 2.4) ;
    l'identifiant de la réservation renvoyé sert à la suite du parcours
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Bloquer des places côte à côte",
        tags=["Réservation"],
        request=HoldSerializer,
        responses={
            201: BookingHoldSerializer,
            400: OpenApiResponse(description="Places non côte à côte"),
            409: OpenApiResponse(description="Une des places est déjà prise"),
        },
    )
    def post(self, request):
        release_expired_bookings()
        serializer = HoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = hold_seats(
                serializer.validated_data["screening"],
                serializer.validated_data["seats"],
            )
        except IntegrityError as error:
            # Seule une place déjà prise donne un conflit (409) ; toute
            # autre erreur de la base n'est pas masquée
            if "unique_seat_per_screening" not in str(error):
                raise
            return Response(
                {"detail": SEAT_TAKEN}, status=status.HTTP_409_CONFLICT
            )
        return Response(
            BookingHoldSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )
