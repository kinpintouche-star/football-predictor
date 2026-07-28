# API Football Predictor

API FastAPI qui lit les données depuis Neon.

## Structure

```text
app/main.py      # demarrage FastAPI
app/routes.py    # endpoints API
app/methods.py   # requetes SQL et regles metier
```

## .env

En local, créer `api_football_predictor/.env` :

```txt
NEON_DATABASE_URL=postgresql://user:password@host/database?sslmode=require
```

Avec Docker Compose, cette variable est lue depuis le `.env` à la racine du projet.

## Lancer en local

```bash
cd api_football_predictor
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoint principal

```text
GET /teams/{search}
GET /team/{team_id}
GET /player/{player_id}
POST /players
POST /custom/team
POST /custom/tournament
POST /custom/tournament/set
```

## Docker

Le service est lancé par le `docker-compose.yml` racine.

Port interne paramétrable :

```txt
API_SERVER_PORT=8000
```

Port exposé sur la machine :

```txt
API_PORT=8000
```
