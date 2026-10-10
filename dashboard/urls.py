"""Routes du pilotage, préfixées par /api/dashboard/"""

from django.urls import path

from dashboard.views import KpiCsvView, KpiView, OccupancyView

urlpatterns = [
    path("occupancy/", OccupancyView.as_view(), name="occupancy"),
    path("kpi/", KpiView.as_view(), name="kpi"),
    path("kpi/csv/", KpiCsvView.as_view(), name="kpi-csv"),
]
