"""API des comptes : connexion et compte connecté (US 9.1)"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.serializers import LoginSerializer, MeSerializer


@extend_schema_view(
    post=extend_schema(summary="Connexion du personnel", tags=["Comptes"])
)
class LoginView(TokenObtainPairView):
    """Connexion par e-mail et mot de passe, renvoie un jeton JWT

    Le verrouillage après 5 échecs est géré par accounts/backends.py
    """

    serializer_class = LoginSerializer


@extend_schema(
    summary="Compte connecté", responses=MeSerializer, tags=["Comptes"]
)
@api_view(["GET"])
def me(request):
    """Renvoie le compte connecté (jeton obligatoire, sinon 401)"""
    return Response(MeSerializer(request.user).data)
