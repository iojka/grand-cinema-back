"""Tableaux de bord du pilotage (EPIC 8)"""

from datetime import date, timedelta

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import HasRole
from dashboard.services import occupancy


def read_date(request, name, default):
    """Lit une date dans l'adresse, par exemple ?start=2026-10-01

    :param request: requête reçue
    :param name: nom du paramètre
    :param default: date utilisée si le paramètre est absent
    :return: la date lue
    :raises ValidationError: si la date est mal écrite (400)
    """
    text = request.query_params.get(name)
    if text is None:
        return default
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValidationError(
            {name: "Date attendue au format AAAA-MM-JJ."}
        ) from None


class OccupancyView(APIView):
    """Tableau de bord du remplissage pour Isabelle (US 8.1)

    Réservé à l'administration et à la direction (US 9.1)
    """

    permission_classes = [HasRole]
    allowed_roles = [User.Role.ADMIN, User.Role.MANAGEMENT]

    @extend_schema(
        summary="Tableau de bord du remplissage",
        tags=["Pilotage"],
        parameters=[
            OpenApiParameter(
                "start", str, description="Premier jour (AAAA-MM-JJ)"
            ),
            OpenApiParameter(
                "end", str, description="Dernier jour (AAAA-MM-JJ)"
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "Taux par séance, salle, jour et semaine ; "
                    "ventes web et guichet"
                )
            ),
            400: OpenApiResponse(description="Période mal écrite"),
        },
    )
    def get(self, request):
        # Par défaut : les 7 derniers jours, aujourd'hui compris
        today = timezone.localdate()
        start = read_date(request, "start", today - timedelta(days=6))
        end = read_date(request, "end", today)
        if start > end:
            raise ValidationError(
                {"start": "Le début de la période doit précéder la fin."}
            )
        return Response(occupancy(start, end))
