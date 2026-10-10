"""API publique du programme et des fiches films (US 1.1 et 1.3)"""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from programme.models import Movie, next_screenings
from programme.serializers import MovieDetailSerializer, ScreeningSerializer


@extend_schema(summary="Programme des 7 prochains jours", tags=["Programme"])
class ProgrammeView(ListAPIView):
    """Séances programmées des 7 prochains jours, triées par date et heure

    Route publique : le spectateur n'a pas besoin de compte (US 2.4)
    """

    serializer_class = ScreeningSerializer
    permission_classes = [AllowAny]
    # Toute la semaine en une seule réponse (pas de pages)
    pagination_class = None

    def get_queryset(self):
        return next_screenings()


@extend_schema(summary="Fiche d'un film", tags=["Programme"])
class MovieDetailView(RetrieveAPIView):
    """Fiche d'un film et ses prochaines séances (US 1.3)

    Route publique ; un film inconnu renvoie une erreur 404
    """

    queryset = Movie.objects.all()
    serializer_class = MovieDetailSerializer
    permission_classes = [AllowAny]
