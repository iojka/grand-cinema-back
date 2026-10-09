"""API de la réservation : plan, blocage, panier (US 2.1 à 3.3), guichet
(US 7.2) et suivi des réservations (US 7.1)
"""

from datetime import date

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    RetrieveDestroyAPIView,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasRole
from booking.models import Booking, Ticket
from booking.serializers import (
    BookingHoldSerializer,
    BookingSerializer,
    BoxOfficeBookingSerializer,
    BoxOfficeSaleSerializer,
    ConfirmationSerializer,
    CustomerSerializer,
    HoldSerializer,
    SeatMapSerializer,
    TicketPriceSerializer,
    TrackingSerializer,
)
from booking.services import (
    cancel_booking,
    change_ticket_price,
    hold_seats,
    release_expired_bookings,
    sell_at_box_office,
)
from programme.models import Screening, next_screenings

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


@extend_schema_view(
    get=extend_schema(summary="Panier d'une réservation en attente"),
    delete=extend_schema(summary="Annuler le panier pour changer de places"),
)
@extend_schema(tags=["Réservation"])
class BookingView(RetrieveDestroyAPIView):
    """Panier : places bloquées, tarifs proposés et total (US 2.3)

    L'identifiant de la réservation (UUID non devinable) sert de clé au
    spectateur sans compte ; une réservation expirée renvoie une 404.
    DELETE annule le panier pour que le spectateur change de places
    """

    serializer_class = BookingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        release_expired_bookings()
        return Booking.objects.filter(status=Booking.Status.PENDING)

    def perform_destroy(self, instance):
        # On garde la trace de la réservation : annulée, places libérées
        cancel_booking(instance)


class TicketPriceView(APIView):
    """Choix du tarif d'une place du panier (US 2.3)"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Choisir le tarif d'une place",
        tags=["Réservation"],
        request=TicketPriceSerializer,
        responses={
            200: BookingSerializer,
            400: OpenApiResponse(description="Tarif inconnu ou désactivé"),
            404: OpenApiResponse(description="Panier expiré ou inconnu"),
        },
    )
    def patch(self, request, pk, ticket_id):
        release_expired_bookings()
        ticket = get_object_or_404(
            Ticket,
            pk=ticket_id,
            booking_id=pk,
            booking__status=Booking.Status.PENDING,
        )
        serializer = TicketPriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = change_ticket_price(
            ticket, serializer.validated_data["price"]
        )
        return Response(BookingSerializer(booking).data)


class CustomerView(APIView):
    """Coordonnées du spectateur sans compte (US 2.4)"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Enregistrer les coordonnées du spectateur",
        tags=["Réservation"],
        request=CustomerSerializer,
        responses={
            200: BookingSerializer,
            400: OpenApiResponse(description="Coordonnées incomplètes"),
            404: OpenApiResponse(description="Panier expiré ou inconnu"),
        },
    )
    def patch(self, request, pk):
        release_expired_bookings()
        booking = get_object_or_404(
            Booking, pk=pk, status=Booking.Status.PENDING
        )
        serializer = CustomerSerializer(booking, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BookingSerializer(booking).data)


@extend_schema(summary="Récapitulatif de la réservation", tags=["Réservation"])
class ConfirmationView(RetrieveAPIView):
    """Récapitulatif affiché après le paiement (US 3.3)

    Statut PENDING : Stripe n'a pas encore confirmé le paiement, le front
    relit la route. Une réservation expirée ou annulée renvoie une 404 :
    pas de confirmation sans paiement (critère 3)
    """

    serializer_class = ConfirmationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        release_expired_bookings()
        return Booking.objects.filter(
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
        )


class BoxOfficeSaleView(APIView):
    """Vente au guichet par un agent d'accueil (US 7.2)

    Réservée au personnel du guichet : le rôle est vérifié par HasRole
    (US 9.1). La vente est confirmée et payée tout de suite
    """

    permission_classes = [HasRole]
    allowed_roles = [User.Role.BOX_OFFICE, User.Role.ADMIN]

    @extend_schema(
        summary="Vendre des places au guichet",
        tags=["Guichet"],
        request=BoxOfficeSaleSerializer,
        responses={
            201: BoxOfficeBookingSerializer,
            400: OpenApiResponse(description="Vente incomplète"),
            401: OpenApiResponse(description="Agent non connecté"),
            403: OpenApiResponse(description="Rôle non autorisé"),
            409: OpenApiResponse(description="Une des places est déjà prise"),
        },
    )
    def post(self, request):
        release_expired_bookings()
        serializer = BoxOfficeSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            booking = sell_at_box_office(
                data["screening"],
                data["tickets"],
                data["payment_method"],
                request.user,
            )
        except IntegrityError as error:
            # Place prise en ligne ou à un autre guichet (critère 2)
            if "unique_seat_per_screening" not in str(error):
                raise
            return Response(
                {"detail": SEAT_TAKEN}, status=status.HTTP_409_CONFLICT
            )
        return Response(
            BoxOfficeBookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Suivi des réservations par séance",
    tags=["Suivi"],
    parameters=[
        OpenApiParameter(
            "date",
            str,
            description="Jour suivi (AAAA-MM-JJ), aujourd'hui par défaut",
        )
    ],
)
class TrackingView(ListAPIView):
    """Séances d'un jour avec leurs ventes, pour Isabelle (US 7.1)

    Réservé à l'administration, à la direction et à l'accueil (US 9.1)
    """

    serializer_class = TrackingSerializer
    permission_classes = [HasRole]
    allowed_roles = [
        User.Role.ADMIN,
        User.Role.MANAGEMENT,
        User.Role.BOX_OFFICE,
    ]
    pagination_class = None  # toutes les séances du jour

    def get_queryset(self):
        # Jour choisi (critère 3), sinon aujourd'hui (critère 1)
        text = self.request.query_params.get("date")
        if text is None:
            day = timezone.localdate()
        else:
            try:
                day = date.fromisoformat(text)
            except ValueError:
                raise ValidationError(
                    {"date": "Date attendue au format AAAA-MM-JJ."}
                ) from None
        return (
            Screening.objects.filter(starts_at__date=day)
            .exclude(status=Screening.Status.CANCELLED)
            .select_related("movie", "room")
            .order_by("starts_at")
        )
