"""Routes du pilotage, préfixées par /api/dashboard/"""

from django.urls import path

from dashboard.views import OccupancyView

urlpatterns = [
    path("occupancy/", OccupancyView.as_view(), name="occupancy"),
]
