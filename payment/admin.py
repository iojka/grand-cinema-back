"""Back office des notifications Stripe (lecture seule)"""

from django.contrib import admin

from payment.models import StripeEvent


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    """Journal des notifications, non modifiable"""

    list_display = ("event_id", "event_type", "booking", "received_at")
    readonly_fields = ("event_id", "event_type", "booking", "received_at")
