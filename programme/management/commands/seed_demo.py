"""Données de démonstration : quelques films fictifs et leurs séances

Usage : python manage.py seed_demo --days 120
Crée 4 films fictifs (titres et synopsis inventés, pour ne pas utiliser
d'oeuvres protégées) et 2 séances par jour pour
chacun, à partir d'aujourd'hui. On voit ainsi toujours un
programme sur les 7 prochains jours.
La commande peut être relancée sans créer de doublons. Un créneau
déjà occupé par une autre séance (US 6.1) est ignoré.
Prérequis : les salles de seed_cinema
"""

from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from programme.models import Movie, Room, Screening

Rating = Movie.Rating
Version = Movie.Version

# (titre, synopsis, durée, classification, version, jeune public, salle)
MOVIES = [
    (
        "Les notes du Causse",
        "Une jeune musicienne quitte Paris pour le festival de jazz "
        "de Mende et y retrouve le goût de jouer.",
        105,
        Rating.ALL,
        Version.VF,
        False,
        "Salle 1 - IMAX",
    ),
    (
        "Les robots de l'espace",
        "Des robots de l'espace vivent des aventures intergalactiques. "
        "Un film d'animation pour les plus jeunes.",
        80,
        Rating.ALL,
        Version.VF,
        True,
        "Salle 3",
    ),
    (
        "Minuit sur l'Aubrac",
        "Une nuit d'hiver, une gendarme enquête sur la disparition "
        "d'un randonneur dans la piste de la bête du Gévaudan.",
        118,
        Rating.UNDER_12,
        Version.VOST,
        False,
        "Salle 7 - VIP",
    ),
    (
        "La dernière séance",
        "Le projectionniste d'un vieux cinéma prépare sa dernière "
        "soirée avant la retraite.",
        96,
        Rating.ALL,
        Version.VF,
        False,
        "Salle 9 - Événementielle",
    ),
]

# Deux séances par jour pour chaque film
HOURS = [time(14, 0), time(20, 30)]


class Command(BaseCommand):
    """Commande manage.py qui crée les données de démonstration"""

    help = "Crée 4 films fictifs et leurs séances (2 par jour)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=120,
            help="nombre de jours de séances à créer (120 par défaut)",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Crée les films et les séances manquants en une transaction

        :raises CommandError: si les salles de seed_cinema n'existent pas
        """
        today = timezone.localdate()
        created = 0
        skipped = 0
        for movie_data in MOVIES:
            title, synopsis, duration, rating, version, young, room_name = (
                movie_data
            )
            try:
                room = Room.objects.get(name=room_name)
            except Room.DoesNotExist as error:
                raise CommandError(
                    "Salles introuvables : lancez d'abord seed_cinema."
                ) from error

            movie, _ = Movie.objects.get_or_create(
                title=title,
                defaults={
                    "synopsis": synopsis,
                    "duration_minutes": duration,
                    "rating": rating,
                    "version": version,
                    "is_young_audience": young,
                },
            )
            for day in range(options["days"]):
                date = today + timedelta(days=day)
                for hour in HOURS:
                    starts_at = timezone.make_aware(
                        datetime.combine(date, hour)
                    )
                    try:
                        _, is_new = Screening.objects.get_or_create(
                            movie=movie, room=room, starts_at=starts_at
                        )
                    except ValidationError:
                        # La salle est déjà prise sur ce créneau
                        skipped += 1
                        continue
                    if is_new:
                        created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(MOVIES)} films, {created} séances créées, "
                f"{skipped} créneaux déjà occupés."
            )
        )
