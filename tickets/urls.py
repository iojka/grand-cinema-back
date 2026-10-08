"""Routes des billets, préfixées par /api/tickets/"""

from django.urls import path

from tickets.views import ticket_qr

urlpatterns = [
    path("<uuid:pk>/qr/", ticket_qr, name="ticket-qr"),
]
