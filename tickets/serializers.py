"""Données échangées pour le contrôle des billets à l'entrée (US 7.3)"""

from rest_framework import serializers

from booking.models import Booking, Ticket
from booking.serializers import BookingScreeningSerializer
from programme.models import Screening
from tickets.services import (
    ALREADY_SCANNED,
    INVALID,
    OTHER_SCREENING,
    VALID,
)


class ScanSerializer(serializers.Serializer):
    """Scan : séance contrôlée par l'agent et texte lu dans le QR code"""

    screening = serializers.PrimaryKeyRelatedField(
        queryset=Screening.objects.all()
    )
    code = serializers.CharField(max_length=200)


class ScannedTicketSerializer(serializers.ModelSerializer):
    """Billet scanné : séance (film, salle, date), place, 1er passage"""

    reference = serializers.CharField(source="booking.reference")
    screening = BookingScreeningSerializer(read_only=True)
    seat = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ["reference", "screening", "seat", "scanned_at"]

    def get_seat(self, ticket) -> str:
        """Place affichée sous la forme « A1 »"""
        return f"{ticket.seat.row}{ticket.seat.number}"


class ScanResultSerializer(serializers.Serializer):
    """Résultat du scan : écran vert, rouge ou orange (documentation)"""

    result = serializers.ChoiceField(
        choices=[VALID, ALREADY_SCANNED, OTHER_SCREENING, INVALID]
    )
    ticket = ScannedTicketSerializer(allow_null=True)


class EntrySerializer(serializers.ModelSerializer):
    """Réservation de la liste de la séance (mode dégradé, critère 4)"""

    seats = serializers.SerializerMethodField()
    # Calculé par screening_entries() : heure du 1er passage
    scanned_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Booking
        fields = ["id", "reference", "seats", "scanned_at"]

    def get_seats(self, booking) -> list[str]:
        """Places de la réservation, par exemple ["A1", "A2"]"""
        seats = []
        for ticket in booking.tickets.all():
            seats.append(f"{ticket.seat.row}{ticket.seat.number}")
        return seats
