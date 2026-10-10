# grand-cinema-back
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=iojka_grand-cinema-back&metric=alert_status)](https://sonarcloud.io/project/overview?id=iojka_grand-cinema-back) [![Couverture](https://sonarcloud.io/api/project_badges/measure?project=iojka_grand-cinema-back&metric=coverage)](https://sonarcloud.io/component_measures?id=iojka_grand-cinema-back&metric=coverage&view=list) [![Sécurité](https://sonarcloud.io/api/project_badges/measure?project=iojka_grand-cinema-back&metric=security_rating)](https://sonarcloud.io/component_measures?id=iojka_grand-cinema-back&metric=security_rating&view=list)

API de réservation pour Le Grand Cinéma (Django et DRF) : 10 salles et 1 700 places

L'objectif du projet est d'augmenter la fréquentation de 30% en 12 mois, surtout pendant le festival de jazz. 
L'application dessert cet objectif en permettant de consulter le programme, voir les places disponibles en temps réel, réserver sa ou ses places, payer en ligne et recevoir un billet dématérialisé. Côté cinéma, elle permet de gérer la programmation, suivre les réservation et analyser le remplissages des salles notamment. Pour plus de détail cf. documents de conception et de gestion de l'app (blocs 1 et 2)

Liens du projet : 
- Dépôt front end (React) : https://github.com/iojka/grand-cinema-front
- Product Backlog : https://trello.com/b/Z7q5iFj3/le-grand-cinema-product-backlog-by-marine
- Application (préproduction) : https://brave-meadow-061c73103.4.azurestaticapps.net
- Documentation de l'API (Swagger) : https://ca-grandcinema-preprod-fr.niceriver-d1b5328b.francecentral.azurecontainerapps.io/api/docs/
- Back office (admin Django) : https://ca-grandcinema-preprod-fr.niceriver-d1b5328b.francecentral.azurecontainerapps.io/admin/
- Qualité du code (SonarQube Cloud) : https://sonarcloud.io/summary/overall?id=iojka_grand-cinema-back&branch=develop

Premier chargement : 20 à 30 secondes possibles (l'API s'arrête sans visite pour limiter le coût).

## Périmètre

Ce dépôt contient le MVP défini avec la méthode MoSCoW (US avec "Must") du backlog Trello.

## Socle technique : 
- Python / Django avec DJango Rest Framework (DRF) : API REST, interface d'admin (back office), auth, ORM
- PostgreSQL : base de données (transactions et verrouillage des places pour éviter la double vente entre le site et le guichet)
- Stripe : paiement en ligne par page de paiement hébergée
- MS Azure (France Central) : hébergement en services managés (PaaS : container apps pour l'API, PostgreSQL Flexible Server)
- GitHub Actions : intégration continue (analyse du code, tests et couverture)

## Organisation des branches

cf. CONTRIBUTING.md

## Tests et qualité du code

- Tests : pytest et pytest-django (184 tests), écrits avant le code (TDD)
- Couverture : `pytest --cov --cov-report=term-missing` (98 %)
- Analyse : Ruff (style PEP 8, bugs probables, sécurité) avec `ruff check .` et `ruff format --check .`
- Intégration continue (GitHub Actions) : Ruff, migrations, tests et couverture, puis SonarQube Cloud (quality gate sur chaque PR)
- Livraison continue : image Docker publiée sur ghcr.io puis déployée sur Azure Container Apps à chaque fusion sur develop
- Sécurité : scan OWASP ZAP de la préproduction lancé à la main (onglet Actions)

## Auteur

Marine Crognier (Bachelor Développeur d'application Python, Bloc 3 "Développer une solution digitale") - session décembre 2026