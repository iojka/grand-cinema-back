"""Routes de l'API des comptes, préfixées par /api/auth/"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import LoginView, me

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    # Nouveau jeton d'accès quand le précédent a expiré
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", me, name="me"),
]
