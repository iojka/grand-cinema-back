"""Connexion du personnel avec verrouillage du compte (US 9.1)

Ce backend est utilisé par l'admin Django et par l'API (connexion JWT) :
les mêmes règles s'appliquent partout
"""

import logging

from django.contrib.auth.backends import ModelBackend

from accounts.models import User

logger = logging.getLogger("accounts")


class LockoutBackend(ModelBackend):
    """Connexion par e-mail et mot de passe, avec verrouillage

    Les tentatives sont journalisées avec le numéro du compte, jamais
    avec le mot de passe ni l'e-mail (RGPD)
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Vérifie les identifiants et applique les règles de l'US 9.1

        :param request: requête HTTP (admin ou API)
        :param username: e-mail saisi (l'API l'envoie dans kwargs["email"])
        :param password: mot de passe saisi
        :return: le compte si la connexion est acceptée, sinon None
        """
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            logger.warning("Connexion refusée : compte inconnu")
            return None

        if not user.is_active:
            logger.warning(
                "Connexion refusée : compte désactivé (n°%s)", user.pk
            )
            return None
        if user.is_locked():
            logger.warning(
                "Connexion refusée : compte verrouillé (n°%s)", user.pk
            )
            return None
        if not user.check_password(password):
            user.register_failed_login()
            logger.warning(
                "Connexion refusée : mauvais mot de passe (n°%s)", user.pk
            )
            return None

        user.reset_failed_logins()
        logger.info("Connexion réussie (compte n°%s)", user.pk)
        return user
