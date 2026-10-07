"""Données échangées par l'API des comptes (US 9.1)"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import User


class LoginSerializer(TokenObtainPairSerializer):
    """Connexion : renvoie un jeton JWT qui contient le rôle du compte"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Comme dans l'exemple du cours, le rôle est placé dans le jeton
        token["role"] = user.role
        return token


class MeSerializer(serializers.ModelSerializer):
    """Compte connecté, affiché par le front (nom, rôle)"""

    role_label = serializers.CharField(
        source="get_role_display", read_only=True
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "role_label"]
