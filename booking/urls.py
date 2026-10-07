"""Routes de l'API de réservation, préfixées par /api/booking/"""

from django.urls import path

from booking.views import HoldView, SeatMapView

urlpatterns = [
    path(
        "screenings/<int:pk>/seats/",
        SeatMapView.as_view(),
        name="seat-map",
    ),
    path("holds/", HoldView.as_view(), name="holds"),
]
