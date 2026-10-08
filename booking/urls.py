"""Routes de l'API de réservation, préfixées par /api/booking/"""

from django.urls import path

from booking.views import (
    BookingView,
    ConfirmationView,
    CustomerView,
    HoldView,
    SeatMapView,
    TicketPriceView,
)

urlpatterns = [
    path(
        "screenings/<int:pk>/seats/",
        SeatMapView.as_view(),
        name="seat-map",
    ),
    path("holds/", HoldView.as_view(), name="holds"),
    path("bookings/<uuid:pk>/", BookingView.as_view(), name="booking"),
    path(
        "bookings/<uuid:pk>/customer/",
        CustomerView.as_view(),
        name="booking-customer",
    ),
    path(
        "bookings/<uuid:pk>/confirmation/",
        ConfirmationView.as_view(),
        name="booking-confirmation",
    ),
    path(
        "bookings/<uuid:pk>/tickets/<uuid:ticket_id>/",
        TicketPriceView.as_view(),
        name="ticket-price",
    ),
]
