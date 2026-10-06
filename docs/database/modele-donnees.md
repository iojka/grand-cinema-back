# Modèle de données – Le Grand Cinéma

Diagramme de classes UML des tables de l'application (une classe = une table, nom au pluriel en snake_case).
Les attributs techniques hérités de Django pour les comptes (dernière connexion, groupes…) ne sont pas détaillés.

```mermaid
classDiagram
    direction LR

    class users {
        id : bigint PK
        email : varchar(254) UNIQUE
        password : varchar(128) haché
        first_name, last_name : varchar(150)
        role : ADMIN | PROGRAMMING | BOX_OFFICE | MANAGEMENT
        is_active : boolean
    }
    class movies {
        id : bigint PK
        title : varchar(200)
        synopsis : text
        duration_minutes : smallint
        poster : varchar(100)
        rating : TP | -12 | -16 | -18
        version : VF | VOST
        is_young_audience : boolean
    }
    class rooms {
        id : bigint PK
        name : varchar(50) UNIQUE
        category : PREMIUM | STANDARD | VIP | EVENT
        supplement : decimal(5,2)
    }
    class seats {
        id : bigint PK
        room_id : FK
        row : varchar(2)
        number : smallint
        is_accessible : boolean
        is_active : boolean
        UNIQUE(room_id, row, number)
    }
    class prices {
        id : bigint PK
        label : varchar(50) UNIQUE
        amount : decimal(6,2)
        requires_proof : boolean
        is_active : boolean
    }
    class screenings {
        id : bigint PK
        movie_id : FK
        room_id : FK
        starts_at : timestamptz INDEX
        status : SCHEDULED | CANCELLED
    }
    class bookings {
        id : uuid PK
        reference : varchar(8) UNIQUE
        screening_id : FK
        channel : WEB | BOX_OFFICE
        status : PENDING | CONFIRMED | EXPIRED | CANCELLED
        customer_name, customer_email, customer_postcode, customer_country
        total_amount : decimal(7,2)
        payment_method : ONLINE_CARD | CASH | CARD_TERMINAL
        stripe_session_id : varchar(255) UNIQUE
        expires_at, created_at, confirmed_at : timestamptz
        sold_by_id : FK nullable
    }
    class tickets {
        id : uuid PK
        booking_id : FK
        screening_id : FK
        seat_id : FK
        price_id : FK
        unit_price : decimal(6,2)
        status : HELD | SOLD
        scanned_at : timestamptz
        scanned_by_id : FK nullable
        UNIQUE(screening_id, seat_id)
    }
    class stripe_events {
        id : bigint PK
        event_id : varchar(255) UNIQUE
        event_type : varchar(100)
        received_at : timestamptz
        booking_id : FK nullable
    }

    rooms "1" *-- "1..*" seats : comporte
    movies "1" -- "0..*" screenings : est projeté
    rooms "1" -- "0..*" screenings : accueille
    screenings "1" -- "0..*" bookings : concerne
    bookings "1" *-- "1..*" tickets : contient
    screenings "1" -- "0..*" tickets : occupe
    seats "1" -- "0..*" tickets : est attribuée
    prices "1" -- "0..*" tickets : s'applique
    users "0..1" -- "0..*" bookings : vend au guichet
    users "0..1" -- "0..*" tickets : scanne
    bookings "0..1" -- "0..*" stripe_events : notifie
```

## Règles portées par la base

| Règle métier | Mise en œuvre | US |
|---|---|---|
| Pas de double vente (web et guichet) | UNIQUE(screening_id, seat_id) sur tickets | 2.2, 7.2 |
| Place libre / bloquée / vendue | libre = pas de ligne ; bloquée = HELD + bookings.expires_at ; vendue = SOLD | 2.1, 2.2 |
| Notification Stripe traitée une seule fois | UNIQUE(event_id) sur stripe_events | 3.1 |
| Prix payé inchangé si le tarif évolue | tickets.unit_price figé à la vente | 6.2 |
| Séance avec réservations non supprimable | clé étrangère ON DELETE PROTECT | 6.1 |
| Pas de chevauchement de séances (durée + 15 min) | contrôle applicatif Screening.clean() | 6.1 |
| Aucune donnée de carte bancaire | seul stripe_session_id est conservé | 3.1 |
| Identifiants non prévisibles | UUID pour bookings et tickets (QR code) | 4.1 |
