# SQL Agent

Service FastAPI read-only qui permet au front de poser des questions sur Neon.

## Variables d'environnement

```txt
NEON_DATABASE_URL=postgresql://user:password@host/database?sslmode=require
LIGHTNING_API_KEY=...
LLM_MODEL=google/gemini-3.5-flash
LLM_MAX_RESPONSE_TOKENS=1600
SQL_AGENT_SERVER_PORT=8100
```

Idealement, `NEON_DATABASE_URL` doit pointer vers un user Neon en lecture seule.
`LLM_MAX_RESPONSE_TOKENS` est optionnel et controle la longueur cible des
reponses de l'agent quand le SDK du modele l'accepte.

## Lancer en local

```bash
cd sql_agent
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

## Hebergement Lightning AI

Dans un Studio Lightning, lancer le meme service :

```bash
cd sql_agent
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8100
```

Puis exposer le port `8100` avec API Builder ou Port viewer.

Test rapide depuis l'URL exposee :

```bash
curl https://ton-url-lightning/health
```

Puis :

```bash
curl -X POST https://ton-url-lightning/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Quels sont les 10 attaquants les mieux notes sous 50 millions ?","max_rows":10}'
```

## Endpoints

```text
GET /health
GET /schema
POST /chat
```

Exemple :

```json
{
  "message": "Quels sont les 10 attaquants les mieux notes sous 50 millions ?",
  "max_rows": 10
}
```

L'agent valide la requete SQL, refuse toute ecriture, puis l'execute dans une transaction PostgreSQL read-only.
