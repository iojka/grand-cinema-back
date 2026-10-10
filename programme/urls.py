"""Routes de l'API du programme, préfixées par /api/programme/"""

from django.urls import path

from programme.views import MovieDetailView, ProgrammeView

urlpatterns = [
    path("", ProgrammeView.as_view(), name="programme"),
    path("movies/<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
]
