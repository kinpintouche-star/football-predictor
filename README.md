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