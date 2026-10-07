"""Droits d'accès à l'API selon le rôle du compte (US 9.1)"""

from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    """Autorise seulement les rôles listés dans la vue (allowed_roles)

    Exemple pour le guichet : allowed_roles = [User.Role.BOX_OFFICE].
    Sans le bon rôle, l'API refuse l'accès (403)
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        allowed_roles = getattr(view, "allowed_roles", [])
        return request.user.role in allowed_roles
