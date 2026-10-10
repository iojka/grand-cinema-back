"""Back office des réservations, en lecture (suivi complet : US 7.1)"""

from django.contrib import admin

from booking.models import Booking, Ticket


class TicketInline(admin.TabularInline):
    """Billets affichés dans la fiche de leur réservation"""

    model = Ticket
    extra = 0
    readonly_fields = (
        "seat",
        "price",
        "unit_price",
        "status",
        "scanned_at",
        "scanned_by",
    )
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Liste des réservations, avec recherche par référence ou client"""

    list_display = (
        "reference",
        "screening",
        "channel",
        "status",
        "total_amount",
        "created_at",
    )
    list_filter = ("channel", "status")
    search_fields = ("reference", "customer_name", "customer_email")
    readonly_fields = (
        "reference",
        "created_at",
        "confirmed_at",
        "stripe_session_id",
    )
    inlines = [TicketInline]
