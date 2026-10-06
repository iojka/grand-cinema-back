# grand-cinema-back
API de réservation pour Le Grand Cinéma (Django et DRF) : 10 salles et 1 700 places

L'objectif du projet est d'augmenter la fréquentation de 30% en 12 mois, surtout pendant le festival de jazz. 
L'application dessert cet objectif en permettant de consulter le programme, voir les places disponibles en temps réel, réserver sa ou ses places, payer en ligne et recevoir un billet dématérialisé. Côté cinéma, elle permet de gérer la programmation, suivre les réservation et analyser le remplissages des salles notamment. Pour plus de détail cf. documents de conception et de gestion de l'app (blocs 1 et 2)

Liens du projet : 
- Dépôt front end (React) : https://github.com/iojka/grand-cinema-front
- Product Backlog : https://trello.com/b/Z7q5iFj3/le-grand-cinema-product-backlog-by-marine
- Application : en cours
- Documentation de l'API : en cours

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

En cours

## Auteur

Marine Crognier (Bachelor Développeur d'application Python, Bloc 3 "Développer une solution digitale") - session décembre 2026