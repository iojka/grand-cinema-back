"""Plan de salle d'une séance envoyé par l'API (US 2.1)"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from programme.models import Seat
from programme.serializers import ScreeningSerializer

# État d'une place sans billet pour la séance (les autres états sont
# ceux du billet : HELD bloquée, SOLD vendue)
FREE = "FREE"


class SeatSerializer(serializers.ModelSerializer):
    """Place du plan de salle avec son état : FREE, HELD ou SOLD"""

    status = serializers.SerializerMethodField()

    class Meta:
        model = Seat
        fields = ["id", "row", "number", "is_accessible", "status"]

    def get_status(self, seat) -> str:
        """État de la place, lu dans les billets de la séance"""
        taken = self.context["taken"]
        return taken.get(seat.id, FREE)


class SeatMapSerializer(ScreeningSerializer):
    """Séance et toutes les places de sa salle (US 2.1)"""

    seats = serializers.SerializerMethodField()

    class Meta(ScreeningSerializer.Meta):
        fields = ScreeningSerializer.Meta.fields + ["seats"]

    @extend_schema_field(SeatSerializer(many=True))
    def get_seats(self, screening):
        """Places actives de la salle, avec leur état"""
        # Places prises : {id de la place: statut du billet}
        taken = {}
        for ticket in screening.tickets.all():
            taken[ticket.seat_id] = ticket.status
        seats = screening.room.seats.filter(is_active=True)
        return SeatSerializer(seats, many=True, context={"taken": taken}).data
