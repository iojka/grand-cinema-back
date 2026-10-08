"""Billet QR code (US 4.1)

Le QR code ne contient que l'identifiant du billet, signé avec la clé
secrète du serveur (SECRET_KEY, principe HMAC du cours sur les jetons) :
aucune donnée personnelle, et un faux billet sera repéré au scan (US 7.3)
"""

from io import BytesIO

import qrcode
from django.core.signing import Signer


def ticket_token(ticket) -> str:
    """Contenu du QR code : l'identifiant du billet signé

    Le « sel » tickets réserve cette signature aux billets

    :param ticket: billet vendu
    :return: une chaîne « identifiant:signature »
    """
    return Signer(salt="tickets").sign(str(ticket.pk))


def qr_code_png(ticket) -> bytes:
    """Dessine le QR code du billet

    :param ticket: billet vendu
    :return: l'image PNG du QR code
    """
    image = qrcode.make(ticket_token(ticket))
    buffer = BytesIO()  # fichier en mémoire
    image.save(buffer, format="PNG")
    return buffer.getvalue()
