"""Données de référence : 10 salles, 1 700 places et la grille tarifaire

Usage : python manage.py seed_cinema
La commande peut être relancée : elle crée seulement ce qui manque et
ne modifie jamais une salle ou un tarif existants. Les prix et
suppléments sont des hypothèses de travail, modifiables par Isabelle
dans le back office (US 6.2)
"""

import string
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from programme.models import Price, Room, Seat

Category = Room.Category

# Capacités du B1 :
# (nom, catégorie, supplément, nombre de rangées, places par rangée)
ROOMS = [
    ("Salle 1 - IMAX", Category.PREMIUM, Decimal("3.00"), 15, 20),  # 300
    ("Salle 2 - Premium", Category.PREMIUM, Decimal("3.00"), 15, 20),  # 300
    ("Salle 3", Category.STANDARD, Decimal("0.00"), 12, 15),  # 180
    ("Salle 4", Category.STANDARD, Decimal("0.00"), 12, 15),  # 180
    ("Salle 5", Category.STANDARD, Decimal("0.00"), 12, 15),  # 180
    ("Salle 6", Category.STANDARD, Decimal("0.00"), 12, 15),  # 180
    ("Salle 7 - VIP", Category.VIP, Decimal("5.00"), 10, 12),  # 120
    ("Salle 8 - VIP", Category.VIP, Decimal("5.00"), 10, 12),  # 120
    ("Salle 9 - Événementielle", Category.EVENT, Decimal("0.00"), 7, 10),
    ("Salle 10 - Événementielle", Category.EVENT, Decimal("0.00"), 7, 10),
]

# Places PMR : les premières places de la rangée A de chaque salle
ACCESSIBLE_SEATS_PER_ROOM = 2

# (libellé, prix, justificatif demandé à l'entrée)
PRICES = [
    ("Plein tarif", Decimal("11.00"), False),
    ("Tarif réduit", Decimal("8.50"), True),
    ("Enfant (moins de 14 ans)", Decimal("6.00"), False),
]


class Command(BaseCommand):
    """Commande manage.py qui charge les données de référence"""

    help = "Crée les 10 salles, leurs 1 700 places et les tarifs."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Crée les salles, places et tarifs manquants en une transaction

        En cas d'erreur, rien n'est enregistré (transaction annulée)
        """
        for name, category, supplement, rows, seats_per_row in ROOMS:
            # get_or_create : une salle existante n'est pas modifiée
            # (le supplément a pu être changé par Isabelle, US 6.2)
            room, _ = Room.objects.get_or_create(
                name=name,
                defaults={"category": category, "supplement": supplement},
            )
            seats = [
                Seat(
                    room=room,
                    row=string.ascii_uppercase[row_index],
                    number=number,
                    is_accessible=(
                        row_index == 0 and number <= ACCESSIBLE_SEATS_PER_ROOM
                    ),
                )
                for row_index in range(rows)
                for number in range(1, seats_per_row + 1)
            ]
            # ignore_conflicts : une place déjà présente (même salle,
            # rangée et numéro) est ignorée grâce à la contrainte d'unicité
            Seat.objects.bulk_create(seats, ignore_conflicts=True)

        for label, amount, requires_proof in PRICES:
            Price.objects.get_or_create(
                label=label,
                defaults={"amount": amount, "requires_proof": requires_proof},
            )

        total_seats = Seat.objects.filter(is_active=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"{Room.objects.count()} salles, {total_seats} places, "
                f"{Price.objects.count()} tarifs."
            )
        )
