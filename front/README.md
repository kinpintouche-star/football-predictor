# Front Football Predictor

Interface Streamlit qui appelle l'API FastAPI.

## .env

En local, créer `front/.env` :

```txt
API_BASE_URL=http://127.0.0.1:8000
SQL_AGENT_API_URL=https://ton-url-lightning
```

Avec Docker Compose, `API_BASE_URL` est injecté automatiquement avec :

```txt
http://api:${API_SERVER_PORT}
```

Le chat data appelle `SQL_AGENT_API_URL`. Sur Render, ajouter cette variable
d'environnement avec l'URL publique Lightning AI de l'agent SQL.

## Lancer en local

Lancer d'abord l'API, puis :

```bash
cd front
python -m pip install -r requirements.txt
streamlit run app.py
```

## Docker

Le service est lancé par le `docker-compose.yml` racine.

Port interne paramétrable :

```txt
FRONT_SERVER_PORT=8501
```

Port exposé sur la machine :

```txt
FRONT_PORT=8501
```
