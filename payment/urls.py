"""Routes de l'API de paiement, préfixées par /api/payment/"""

from django.urls import path

from payment.views import CheckoutView, StripeWebhookView

urlpatterns = [
    path(
        "bookings/<uuid:pk>/checkout/",
        CheckoutView.as_view(),
        name="checkout",
    ),
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
