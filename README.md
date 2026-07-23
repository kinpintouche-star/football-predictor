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