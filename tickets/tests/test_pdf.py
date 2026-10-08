"""Tests du billet PDF à imprimer (US 4.2)"""

from unittest.mock import patch

import pytest

from booking.services import hold_seats
from tickets.services import qr_code_png, tickets_pdf

pytestmark = pytest.mark.django_db


def test_pdf_is_an_a4_document(paid):
    """Critère 1 : un document PDF au format A4"""
    pdf = tickets_pdf(paid)

    assert pdf.startswith(b"%PDF")
    # Format A4 en points : 595,28 x 841,89
    assert b"595.2756" in pdf
    assert b"841.8898" in pdf


def test_one_page_per_ticket(paid):
    """Une page par place réservée"""
    pdf = tickets_pdf(paid)

    assert b"/Count 2" in pdf


def test_printed_qr_code_is_the_mobile_one(paid):
    """Critère 2 : le PDF reprend le QR code affiché sur le téléphone"""
    ticket = paid.tickets.first()
    # Même billet : même QR code à chaque fois
    assert qr_code_png(ticket) == qr_code_png(ticket)

    # Le PDF utilise la même fonction, pour chacune des 2 places
    with patch("tickets.services.qr_code_png", wraps=qr_code_png) as qr:
        tickets_pdf(paid)

    assert qr.call_count == 2


def test_pdf_can_be_downloaded_again(client, paid):
    """Critère 3 : le billet peut être téléchargé de nouveau"""
    response = client.get(f"/api/tickets/bookings/{paid.pk}/pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert paid.reference in response["Content-Disposition"]


def test_no_pdf_before_payment(client, screening, seats, price):
    """Pas de billet tant que le paiement n'est pas accepté"""
    basket = hold_seats(screening, seats[:1])

    response = client.get(f"/api/tickets/bookings/{basket.pk}/pdf/")

    assert response.status_code == 404
