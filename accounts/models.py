"""M6 Administration : comptes du back office (US 9.1).

Les spectateurs n'ont pas de compte (US 2.4, le compte client US 5.1 est
prévu en V2) : leurs coordonnées sont enregistrées sur la réservation
(booking.Booking).
"""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """Création des comptes : l'adresse e-mail sert d'identifiant."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        """Crée et enregistre un compte avec un mot de passe haché.

        :param email: adresse e-mail, identifiant de connexion
        :param password: mot de passe en clair, haché avant l'enregistrement
        :param extra_fields: autres champs du compte (rôle, nom...)
        :return: le compte créé
        :raises ValueError: si l'adresse e-mail est absente
        """
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        # Hachage par Django : le mot de passe n'est jamais stocké en clair
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self, email: str, password: str | None = None, **extra_fields
    ):
        """Crée un compte du back office (rôle agent d'accueil par défaut).

        :param email: adresse e-mail, identifiant de connexion
        :param password: mot de passe en clair
        :return: le compte créé
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields
    ):
        """Crée un compte administrateur (commande createsuperuser).

        :param email: adresse e-mail, identifiant de connexion
        :param password: mot de passe en clair
        :return: le compte administrateur créé
        :raises ValueError: si is_staff ou is_superuser est forcé à False
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.ADMIN)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError(
                "Un administrateur doit avoir is_staff et is_superuser à True."
            )
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Compte du back office : ID, login (e-mail), mot de passe haché, rôle.

    Les 4 rôles sont ceux de l'US 9.1.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        PROGRAMMING = "PROGRAMMING", "Programmation"
        BOX_OFFICE = "BOX_OFFICE", "Agent d'accueil"
        MANAGEMENT = "MANAGEMENT", "Direction"

    username = None  # remplacé par l'adresse e-mail
    # Le login doit être unique (cours BDR) ; 254 caractères au maximum
    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField(
        "rôle",
        max_length=20,
        choices=Role.choices,
        default=Role.BOX_OFFICE,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["email"]

    def __str__(self) -> str:
        name = self.get_full_name() or self.email
        return f"{name} ({self.get_role_display()})"
