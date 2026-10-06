"""Back office du programme (minimal, enrichi avec les US 6.1 et 6.2)."""

from django.contrib import admin

from programme.models import Movie, Price, Room, Screening, Seat


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """Liste des films."""

    list_display = (
        "title",
        "version",
        "rating",
        "duration_minutes",
        "is_young_audience",
    )
    search_fields = ("title",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Liste des salles avec leur capacité."""

    list_display = ("name", "category", "supplement", "capacity")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    """Liste des places, filtrable par salle."""

    list_display = ("room", "row", "number", "is_accessible", "is_active")
    list_filter = ("room", "is_accessible", "is_active")


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    """Grille tarifaire."""

    list_display = ("label", "amount", "requires_proof", "is_active")


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    """Liste des séances."""

    list_display = ("movie", "room", "starts_at", "status")
    list_filter = ("room", "status")
