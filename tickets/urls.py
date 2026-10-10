"""Routes des billets, préfixées par /api/tickets/"""

from django.urls import path

from tickets.views import (
    CheckInView,
    EntriesView,
    ScanView,
    download_pdf,
    ticket_qr,
)

urlpatterns = [
    path("<uuid:pk>/qr/", ticket_qr, name="ticket-qr"),
    path("bookings/<uuid:pk>/pdf/", download_pdf, name="tickets-pdf"),
    # Contrôle des billets à l'entrée (US 7.3)
    path("scan/", ScanView.as_view(), name="ticket-scan"),
    path(
        "screenings/<int:pk>/entries/",
        EntriesView.as_view(),
        name="screening-entries",
    ),
    path(
        "bookings/<uuid:pk>/checkin/",
        CheckInView.as_view(),
        name="booking-checkin",
    ),
]
