"""Tests du journal des notifications Stripe (US 3.1)"""

import pytest
from django.db import IntegrityError

from payment.models import StripeEvent

pytestmark = pytest.mark.django_db

EVENT_TYPE = "checkout.session.completed"


def test_same_stripe_event_is_recorded_only_once(make_booking):
    """Contrôle anti-doublon : un événement reçu 2 fois est refusé"""
    booking = make_booking()
    StripeEvent.objects.create(
        event_id="evt_test_123", event_type=EVENT_TYPE, booking=booking
    )

    with pytest.raises(IntegrityError):
        StripeEvent.objects.create(
            event_id="evt_test_123", event_type=EVENT_TYPE, booking=booking
        )
