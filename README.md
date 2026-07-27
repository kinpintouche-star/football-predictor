# football-predictor
Predict match results and bests comps based on player stats, teams stats.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Docker Compose

Le projet contient deux services :

- `api` : FastAPI, dans `api_football_predictor/`
- `front` : Streamlit, dans `front/`

Créer un fichier `.env` à la racine :

```txt
NEON_DATABASE_URL=postgresql://user:password@host/database?sslmode=require
API_PORT=8000
API_SERVER_PORT=8000
FRONT_PORT=8501
FRONT_SERVER_PORT=8501
```

Lancer les deux services :

```bash
docker compose up --build
```

URLs locales par défaut :

```text
API   http://127.0.0.1:8000
Front http://127.0.0.1:8501
```


## 6. Notes

- `match` contient une ligne par match.
- `match_team` contient deux lignes par match : une par équipe, avec side, score, coach et formation.
- `lineup` contient une ligne par joueur présent sur la feuille de match, sans répéter les noms de match, équipe ou joueur.
- `lineup.minute_start`, `lineup.minute_end` et `lineup.minutes_played` décrivent le temps passé sur le terrain. Les remplaçants non utilisés ont `minutes_played = 0`.
- `player` contient toutes les données joueur disponibles, avec `has_sofifa_profile` pour distinguer les joueurs enrichis SoFIFA.

## DATA SOFIFA JOUEURS : 
Offensives
Centres              -> crossing
Finition             -> finishing
Précision de la tête -> heading_accuracy
Passes courtes       -> short_passing
Reprise de volée     -> volleys

Technique
Dribble              -> dribbling
Effet                -> curve
Précision CF         -> fk_accuracy
Passes longues       -> long_passing
Contrôle du ballon   -> ball_control

Mouvement
Accélération         -> acceleration
Vitesse              -> sprint_speed
Agilité              -> agility
Réactivité           -> reactions
Equilibre            -> balance

Puissance
Puissance frappe     -> shot_power
Détente              -> jumping
Endurance            -> stamina
Force                -> strength
Tirs de loin         -> long_shots

Etat d'esprit
Agressivité          -> aggression
Interceptions        -> interceptions
Place. off.          -> attack_position
Vista                -> vision
Penaltys             -> penalties
Calme                -> composure

Défense
Conscience défensive -> defensive_awareness
Tacle                -> standing_tackle
Tacle glissé         -> sliding_tackle

Gardien
Plongeon             -> gk_diving
Jeu à la main        -> gk_handling
Jeu au pied          -> gk_kicking
Placement            -> gk_positioning
Réflexes             -> gk_reflexes
