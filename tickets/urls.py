"""Routes des billets, préfixées par /api/tickets/"""

from django.urls import path

from tickets.views import download_pdf, ticket_qr

urlpatterns = [
    path("<uuid:pk>/qr/", ticket_qr, name="ticket-qr"),
    path("bookings/<uuid:pk>/pdf/", download_pdf, name="tickets-pdf"),
]
