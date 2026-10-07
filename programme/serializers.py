"""Données du programme envoyées par l'API (US 1.1)"""

from rest_framework import serializers

from programme.models import Movie, Screening


class MovieSerializer(serializers.ModelSerializer):
    """Informations du film affichées dans le programme"""

    class Meta:
        model = Movie
        fields = [
            "id",
            "title",
            "duration_minutes",
            "rating",
            "version",
            "poster",
            "is_young_audience",
        ]


class ScreeningSerializer(serializers.ModelSerializer):
    """Séance du programme : film, heure, salle et places restantes"""

    movie = MovieSerializer(read_only=True)
    room = serializers.CharField(source="room.name", read_only=True)
    # Valeur calculée par la requête de la vue (annotate)
    remaining_seats = serializers.IntegerField(read_only=True)
    is_full = serializers.SerializerMethodField()

    class Meta:
        model = Screening
        fields = [
            "id",
            "starts_at",
            "movie",
            "room",
            "remaining_seats",
            "is_full",
        ]

    def get_is_full(self, screening) -> bool:
        """Indique si la séance est complète (critère 3 de l'US 1.1)"""
        return screening.remaining_seats <= 0
