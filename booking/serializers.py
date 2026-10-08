"""Données de réservation échangées avec l'API (US 2.1 à 2.4)"""

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from booking.models import Booking, Ticket
from programme.models import Price, Screening, Seat
from programme.serializers import MovieSerializer, ScreeningSerializer

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


class HoldSerializer(serializers.Serializer):
    """Demande de blocage : une séance et des places côte à côte (US 2.2)"""

    screening = serializers.PrimaryKeyRelatedField(
        queryset=Screening.objects.all()
    )
    seats = serializers.PrimaryKeyRelatedField(
        queryset=Seat.objects.filter(is_active=True),
        many=True,
        allow_empty=False,
    )

    def validate_screening(self, screening):
        """Seule une séance programmée et à venir est réservable"""
        if (
            screening.status != Screening.Status.SCHEDULED
            or screening.starts_at <= timezone.now()
        ):
            raise serializers.ValidationError(
                "Cette séance n'est plus réservable."
            )
        return screening

    def validate(self, data):
        """Vérifie que les places sont dans la salle et côte à côte

        Côte à côte : même rangée et numéros qui se suivent ; le maximum
        est donc la taille de la rangée (critère 1)
        """
        screening = data["screening"]
        seats = sorted(data["seats"], key=lambda seat: seat.number)
        for seat in seats:
            if seat.room_id != screening.room_id:
                raise serializers.ValidationError(
                    "Les places doivent être dans la salle de la séance."
                )
        numbers = [seat.number for seat in seats]
        expected = list(range(numbers[0], numbers[0] + len(seats)))
        same_row = len({seat.row for seat in seats}) == 1
        if not same_row or numbers != expected:
            raise serializers.ValidationError(
                "Les places doivent être côte à côte, dans la même rangée."
            )
        data["seats"] = seats
        return data


class BookingHoldSerializer(serializers.ModelSerializer):
    """Réservation en attente renvoyée après le blocage des places"""

    class Meta:
        model = Booking
        fields = ["id", "reference", "expires_at", "total_amount"]


class PriceSerializer(serializers.ModelSerializer):
    """Tarif proposé pour une séance, supplément de la salle compris"""

    amount = serializers.SerializerMethodField()

    class Meta:
        model = Price
        fields = ["id", "label", "amount", "requires_proof"]

    def get_amount(self, price) -> str:
        """Prix d'une place : même calcul qu'au guichet (US 6.2 et 7.2)"""
        return str(price.amount_for(self.context["room"]))


class TicketSerializer(serializers.ModelSerializer):
    """Place du panier avec son tarif et son prix"""

    seat = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ["id", "seat", "price", "unit_price"]

    def get_seat(self, ticket) -> str:
        """Place affichée sous la forme « A1 »"""
        return f"{ticket.seat.row}{ticket.seat.number}"


class BookingScreeningSerializer(serializers.ModelSerializer):
    """Séance rappelée dans le panier"""

    movie = MovieSerializer(read_only=True)
    room = serializers.CharField(source="room.name", read_only=True)

    class Meta:
        model = Screening
        fields = ["id", "starts_at", "room", "movie"]


class BookingSerializer(serializers.ModelSerializer):
    """Panier : séance, places et leur tarif, total, tarifs proposés"""

    screening = BookingScreeningSerializer(read_only=True)
    tickets = TicketSerializer(many=True, read_only=True)
    prices = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "reference",
            "status",
            "expires_at",
            "total_amount",
            "screening",
            "tickets",
            "prices",
            "customer_name",
            "customer_email",
            "customer_postcode",
            "customer_country",
        ]

    @extend_schema_field(PriceSerializer(many=True))
    def get_prices(self, booking):
        """Tarifs actifs paramétrés par Isabelle (critère 1 de l'US 2.3)"""
        prices = Price.objects.filter(is_active=True)
        room = booking.screening.room
        return PriceSerializer(prices, many=True, context={"room": room}).data


class TicketPriceSerializer(serializers.Serializer):
    """Tarif choisi pour une place : seuls les tarifs actifs sont acceptés"""

    price = serializers.PrimaryKeyRelatedField(
        queryset=Price.objects.filter(is_active=True)
    )


class CustomerSerializer(serializers.ModelSerializer):
    """Coordonnées du spectateur sans compte (US 2.4)

    Seuls le nom, l'e-mail (saisi deux fois) et le code postal ou le pays
    sont demandés : minimisation des données (RGPD)
    """

    email_confirmation = serializers.EmailField(write_only=True)

    class Meta:
        model = Booking
        fields = [
            "customer_name",
            "customer_email",
            "email_confirmation",
            "customer_postcode",
            "customer_country",
        ]
        # Champs facultatifs dans le modèle (guichet), obligatoires ici
        extra_kwargs = {
            "customer_name": {"required": True, "allow_blank": False},
            "customer_email": {"required": True, "allow_blank": False},
        }

    def validate_customer_country(self, country):
        """Pays au format ISO à 2 lettres, par exemple DE ou GB"""
        if country and (len(country) != 2 or not country.isalpha()):
            raise serializers.ValidationError(
                "Indiquez le code du pays en 2 lettres (par exemple DE)."
            )
        return country.upper()

    def validate(self, data):
        """Vérifie les deux e-mails et la présence du code postal ou du pays"""
        if data["customer_email"] != data.pop("email_confirmation"):
            raise serializers.ValidationError(
                "Les deux adresses e-mail sont différentes."
            )
        postcode = data.get("customer_postcode", "")
        country = data.get("customer_country", "")
        if not postcode and not country:
            raise serializers.ValidationError(
                "Indiquez votre code postal ou votre pays."
            )
        return data
