"""Vues techniques de l'API."""

from django.db import DatabaseError, connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    summary="Etat de santé de l'API",
    responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT},
    tags=["Technique"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Vérifie que l'API répond et que la base est joignable.

    Sert à Azure Container Apps pour surveiller le conteneur.
    :return: 200 si tout va bien, 503 si la base ne répond pas
    """
    try:
        connection.ensure_connection()
    except DatabaseError:
        return Response({"status": "database unavailable"}, status=503)
    return Response({"status": "ok"})
