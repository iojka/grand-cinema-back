# Convention de branches et de contribution pour l'application Le Grand Cinéma

Ce document CONTRIBUTING.md a pour rôle de fixer les règles de gestion de version des dépôts grand-cinema-back (Django et DRF) et grand-cinema-front (React). Il est destiné à toute l'équipe du projet (chef de projet aussi Scrum master, développeurs).

## 1. Modèle de branches

Le modèle de branches se base sur les bonnes pratiques de développement : main, develop, release, hotfix et feature. Il est adapté au cadre Scum retenu pour le projet (sprints de 2 semaines) et à la livraison continue.

| Branche | Rôle | Créée depuis | Fusionnée vers | Environnement |
|---|---|---|---|---|
| main | Code testé et validé, prêt pour la production. Chaque fusion reçoit un tag de version. | (permanente) | / | Production (déploiement manuel validé par la PO) |
| develop | Intégration des fonctionnalités terminées (DoD respectée). | main (une seule fois) | release/* | Préproduction (déploiement automatique) |
| feature/* | Développement d'une user story du backlog Trello. | develop | develop (pull request) | Local / dev |
| fix/* | Correction d'une anomalie détectée en recette, avant la mise en production. | develop | develop (pull request) | Local / dev |
| release/* | Préparation d'une version : recette par la PO, corrections mineures uniquement. | develop | main puis develop | Préproduction |
| hotfix/* | Correction urgente d'une anomalie bloquante en production. | main | main puis develop | Production |

Les branches main et develop sont protégées et on ne peut y faire aucune modification directe, aucun push ni aucune suppression. Tout doit être mergé sur ces branches via un PR (pull request).

## 2. Règles de nommage des branches

Format : type/reference-description

- Type : feature, fix, release ou hotfix
- Référence : l'identifiant de l'US dans Trello sous la forme usX-X (us2-2 par exemple pour US 2.2), le numéro de version pour release et hotfix
- Description : 2 à 4 mots en anglais sur ce que fait la branche

Contraintes : minuscules, mots séparés par des "-", pas d'accent, ni d'espaces et 50 caractères au max.

Exemple : US 9.1 (comptes et droits) : feature/us9-1-login-user

Règle : une branche pour une US (= une card trello). On rajoute à la card sur Trello le lien de la branche et de la PR.

## 3. Règles de commit

- Un commit est atomique : une seule fonctionnalité ou correction par commit
- Avant chaque commit : git status, git add fichier, git diff puis git commit -m "..."
- Format du message : type(reference): description courte en anglais
- Types utilisés : feat (fonctionnalité), fix (correction), test (tests), docs (documentation), refactor (amélioration du code), chore (config, dépendance)

## 4. Pull requests (PR)

- Une PR d'une branche feature/* ou fix/* cible toujours develop
- Titre au format (exemple) : [US 2.2] Choisir des places côte à côte (back)
- Description : lien vers la card trello, résumé des modifications, critères d'acceptation (Gherkin) vérifiés
- Conditions de fusion (reprises de la DoD) : 
  - Pipeline d'intégration continue au vert (analyse du code, tests unitaires et d'intégration, couverture d'au moins 80% sur le code nouveau, seuil de qualité SonarCloud)
  - Revue de code
  - Aucun conflit avec develop
- Après fusion, suppression de la branche

## 5. Versions

Le format attendu est vMAJEUR.MINEUR.CORRECTIF
Chaque version mise en production est taguée sur main et accompagnée d'une note de version sur GitHub.