"""Back office du programme (droits US 9.1, salles et tarifs US 6.2)"""

from django.contrib import admin

from accounts.models import User
from programme.models import Movie, Price, Room, Screening, Seat


class ProgrammationAccess:
    """Droits des écrans du programme : administrateur et programmation

    Classe ajoutée par héritage aux écrans (ModelAdmin) et aux tableaux
    intégrés (inlines) : les autres rôles ne les voient pas (US 9.1)
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

    def has_add_permission(self, request, obj=None):
        return self.has_role(request)

    def has_change_permission(self, request, obj=None):
        return self.has_role(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_role(request)


class ProgrammationAdmin(ProgrammationAccess, admin.ModelAdmin):
    """Écran du programme réservé à l'administrateur et à la programmation"""


class SeatInline(ProgrammationAccess, admin.TabularInline):
    """Plan de la salle : ses places, modifiables sur la fiche de la salle

    US 6.2 : une place retirée du plan est désactivée plutôt que
    supprimée, pour garder les billets déjà vendus cohérents
    """

    model = Seat
    fields = ("row", "number", "is_accessible", "is_active")
    extra = 0


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
    """Salles : catégorie, supplément et plan de salle (US 6.2)"""

    list_display = ("name", "category", "supplement", "capacity")
    fields = ("name", "category", "supplement", "capacity")
    readonly_fields = ("capacity",)
    inlines = [SeatInline]


@admin.register(Seat)
class SeatAdmin(ProgrammationAdmin):
    """Liste des places, filtrable par salle"""

    list_display = ("room", "row", "number", "is_accessible", "is_active")
    list_filter = ("room", "is_accessible", "is_active")


@admin.register(Price)
class PriceAdmin(ProgrammationAdmin):
    """Grille tarifaire (US 6.2)"""

    list_display = ("label", "amount", "requires_proof", "is_active")


@admin.register(Screening)
class ScreeningAdmin(ProgrammationAdmin):
    """Liste des séances"""

    list_display = ("movie", "room", "starts_at", "status")
    list_filter = ("room", "status")
