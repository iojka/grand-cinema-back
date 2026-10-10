"""Données ajoutées aux pages de l'admin : bandeau des alertes (US 8.3)"""

from django.utils import timezone

from accounts.models import User
from dashboard.models import OccupancyAlert


def occupancy_alerts(request):
    """Alertes de remplissage des séances à venir, pour le bandeau

    Seuls l'administration et la programmation les voient (US 9.1)

    :param request: requête reçue
    :return: les alertes à afficher, rangées sous « occupancy_alerts »
    """
    user = request.user
    if not user.is_authenticated:
        return {}
    if user.role not in (User.Role.ADMIN, User.Role.PROGRAMMING):
        return {}
    alerts = OccupancyAlert.objects.filter(
        screening__starts_at__gte=timezone.now()
    ).select_related("screening__movie", "screening__room")
    return {"occupancy_alerts": alerts}
