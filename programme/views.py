"""API publique du programme (US 1.1)"""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from programme.models import Screening
from programme.serializers import ScreeningSerializer

# US 1.1 : le programme couvre les 7 prochains jours
PROGRAMME_DAYS = 7


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
        now = timezone.now()
        return (
            Screening.objects.filter(
                status=Screening.Status.SCHEDULED,
                starts_at__gte=now,
                starts_at__lt=now + timedelta(days=PROGRAMME_DAYS),
            )
            # Film et salle chargés dans la même requête SQL (jointure)
            .select_related("movie", "room")
            # Places restantes = places actives de la salle - billets
            # de la séance, calculé par la base en une seule requête
            .annotate(
                remaining_seats=Count(
                    "room__seats",
                    filter=Q(room__seats__is_active=True),
                    distinct=True,
                )
                - Count("tickets", distinct=True)
            )
            .order_by("starts_at")
        )
