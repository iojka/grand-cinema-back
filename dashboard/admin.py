"""Back office du pilotage : réglages d'Isabelle et historique des alertes"""

from django.contrib import admin

from accounts.models import User
from dashboard.models import AlertSetting, KpiSetting, OccupancyAlert
from programme.admin import ProgrammationAccess


class AdministrationAccess(ProgrammationAccess):
    """Écrans réservés à l'administrateur (Isabelle) : US 9.1"""

    allowed_roles = [User.Role.ADMIN]


@admin.register(AlertSetting)
class AlertSettingAdmin(AdministrationAccess, admin.ModelAdmin):
    """Seuil d'alerte réglé par Isabelle (critère 1)"""

    list_display = ("__str__", "threshold")

    def has_add_permission(self, request, obj=None):
        # Un seul réglage : Isabelle le modifie au lieu d'en ajouter un
        if AlertSetting.objects.exists():
            return False
        return super().has_add_permission(request, obj)


@admin.register(OccupancyAlert)
class OccupancyAlertAdmin(AdministrationAccess, admin.ModelAdmin):
    """Historique des alertes envoyées, en lecture seule"""

    list_display = ("screening", "fill_rate", "sent_at")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(KpiSetting)
class KpiSettingAdmin(AdministrationAccess, admin.ModelAdmin):
    """Date de lancement et dates du festival (US 8.2)"""

    list_display = ("__str__", "festival_start", "festival_end")

    def has_add_permission(self, request, obj=None):
        # Un seul réglage : Isabelle le modifie au lieu d'en ajouter un
        if KpiSetting.objects.exists():
            return False
        return super().has_add_permission(request, obj)
