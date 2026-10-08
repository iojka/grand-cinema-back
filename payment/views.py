"""API du paiement en ligne avec Stripe (US 3.1)"""

import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from booking.models import Booking
from booking.services import release_expired_bookings
from payment.services import confirm_payment, create_checkout_session


class CheckoutView(APIView):
    """Démarre le paiement du panier sur la page sécurisée de Stripe"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Payer le panier par carte (page Stripe)",
        tags=["Paiement"],
        request=None,
        responses={
            200: inline_serializer(
                name="CheckoutUrl", fields={"url": serializers.URLField()}
            ),
            400: OpenApiResponse(description="Coordonnées manquantes"),
            404: OpenApiResponse(description="Panier expiré ou inconnu"),
        },
    )
    def post(self, request, pk):
        release_expired_bookings()
        booking = get_object_or_404(
            Booking, pk=pk, status=Booking.Status.PENDING
        )
        # Le paiement suit l'étape des coordonnées (US 2.4)
        if not booking.customer_email:
            return Response(
                {"detail": "Indiquez d'abord vos coordonnées."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"url": create_checkout_session(booking)})


class StripeWebhookView(APIView):
    """Notification envoyée par Stripe après un paiement

    Pas de compte ni de jeton : c'est la signature du message qui prouve
    qu'il vient bien de Stripe (clé secrète du webhook)
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(exclude=True)  # route réservée à Stripe
    def post(self, request):
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(
                request.body, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError, stripe.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if event["type"] == "checkout.session.completed":
            confirm_payment(event)
        return Response(status=status.HTTP_200_OK)
