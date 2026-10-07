"""Back office du programme (minimal, enrichi avec les US 6.1 et 6.2)"""

from django.contrib import admin

from accounts.models import User
from programme.models import Movie, Price, Room, Screening, Seat


class ProgrammationAdmin(admin.ModelAdmin):
    """Écrans du programme : administrateur et programmation (US 9.1)

    Les autres rôles ne voient pas ces écrans dans l'admin
    """

    allowed_roles = [User.Role.ADMIN, User.Role.PROGRAMMING]

    def has_role(self, request):
        """Vérifie que le compte connecté a un rôle autorisé"""
        # La page de connexion de l'admin appelle aussi cette méthode,
        # avec un visiteur anonyme qui n'a pas de rôle
        if not request.user.is_authenticated:
            return False
        return request.user.role in self.allowed_roles

    # Mêmes droits pour voir, ajouter, modifier et supprimer
    def has_module_permission(self, request):
        return self.has_role(request)

    def has_view_permission(self, request, obj=None):
        return self.has_role(request)

    def has_add_permission(self, request):
        return self.has_role(request)

    def has_change_permission(self, request, obj=None):
        return self.has_role(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_role(request)


@admin.register(Movie)
class MovieAdmin(ProgrammationAdmin):
    """Liste des films"""

    list_display = (
        "title",
        "version",
        "rating",
        "duration_minutes",
        "is_young_audience",
    )
    search_fields = ("title",)


@admin.register(Room)
class RoomAdmin(ProgrammationAdmin):
    """Liste des salles avec leur capacité"""

    list_display = ("name", "category", "supplement", "capacity")


@admin.register(Seat)
class SeatAdmin(ProgrammationAdmin):
    """Liste des places, filtrable par salle"""

    list_display = ("room", "row", "number", "is_accessible", "is_active")
    list_filter = ("room", "is_accessible", "is_active")


@admin.register(Price)
class PriceAdmin(ProgrammationAdmin):
    """Grille tarifaire"""

    list_display = ("label", "amount", "requires_proof", "is_active")


@admin.register(Screening)
class ScreeningAdmin(ProgrammationAdmin):
    """Liste des séances"""

    list_display = ("movie", "room", "starts_at", "status")
    list_filter = ("room", "status")
