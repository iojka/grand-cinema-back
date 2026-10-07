"""Routes de l'API du programme, préfixées par /api/programme/"""

from django.urls import path

from programme.views import ProgrammeView

urlpatterns = [
    path("", ProgrammeView.as_view(), name="programme"),
]
