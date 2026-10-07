"""Données du programme envoyées par l'API (US 1.1 et 1.3)"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from programme.models import Movie, Screening, next_screenings


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


class MovieScreeningSerializer(serializers.ModelSerializer):
    """Séance d'un film : heure, salle et places restantes"""

    room = serializers.CharField(source="room.name", read_only=True)
    # Valeur calculée par la requête next_screenings (annotate)
    remaining_seats = serializers.IntegerField(read_only=True)
    is_full = serializers.SerializerMethodField()

    class Meta:
        model = Screening
        fields = ["id", "starts_at", "room", "remaining_seats", "is_full"]

    def get_is_full(self, screening) -> bool:
        """Indique si la séance est complète (critère 3 de l'US 1.1)"""
        return screening.remaining_seats <= 0


class ScreeningSerializer(MovieScreeningSerializer):
    """Séance du programme : la séance et son film"""

    movie = MovieSerializer(read_only=True)

    class Meta(MovieScreeningSerializer.Meta):
        fields = MovieScreeningSerializer.Meta.fields + ["movie"]


class MovieDetailSerializer(MovieSerializer):
    """Fiche film : le film, son synopsis et ses prochaines séances"""

    screenings = serializers.SerializerMethodField()

    class Meta(MovieSerializer.Meta):
        fields = MovieSerializer.Meta.fields + ["synopsis", "screenings"]

    @extend_schema_field(MovieScreeningSerializer(many=True))
    def get_screenings(self, movie):
        """Prochaines séances du film (critères 1 et 2 de l'US 1.3)"""
        screenings = next_screenings().filter(movie=movie)
        return MovieScreeningSerializer(screenings, many=True).data
