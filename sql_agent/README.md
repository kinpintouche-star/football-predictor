# SQL Agent

Service FastAPI read-only qui permet au front de poser des questions sur Neon.

## Variables d'environnement

```txt
NEON_DATABASE_URL=postgresql://user:password@host/database?sslmode=require
LIGHTNING_API_KEY=...
LLM_MODEL=openai/gpt-5.4-mini-2026-03-17
LLM_SQL_MODEL=openai/gpt-5.4-mini-2026-03-17
LLM_MAX_RESPONSE_TOKENS=1600
SQL_AGENT_SERVER_PORT=8100
```

Idealement, `NEON_DATABASE_URL` doit pointer vers un user Neon en lecture seule.
`LLM_MODEL=openai/gpt-5.4-mini-2026-03-17` est le choix conseille pour ce
service : plus adapte au SQL que Gemini Flash, sans partir sur un modele premium.
`LLM_SQL_MODEL` est optionnel. Il permet de dedier un modele au SQL; s'il est
absent, le service reprend `LLM_MODEL`.
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

## Pipeline agent

Le service utilise deux roles LLM simples :

1. agent de comprehension : il reformule le besoin en JSON court (`DATA/CHAT`,
   domaine, metrique, style de reponse) ;
2. agent SQL : il ne discute pas, lit seulement l'intention et les templates SQL
   pertinents, puis renvoie une requete `SELECT`.

Apres execution SQL, la reponse retourne au role conversationnel pour produire
une explication humaine a partir des lignes recues.

## Templates SQL

Les templates sont dans `query_templates/`.

Chaque fichier porte le nom du besoin, par exemple :

```text
team_by_name.sql
player_data_by_name.sql
players_of_team_by_name.sql
custom_team_by_name.sql
custom_team_by_id.sql
custom_team_players_by_id.sql
matches_of_team_by_name.sql
best_real_teams_by_uefa_rank.sql
best_players_by_overall.sql
tournaments_list.sql
tournament_by_name.sql
tournament_by_id.sql
tournament_winner_by_name.sql
tournament_winner_by_id.sql
tournament_matches_with_winners.sql
```

Le fichier `app/query_templates.py` choisit les templates pertinents par
mots-cles. Pour les questions evidentes, comme "meilleure equipe", le SQL du
template est execute directement. Pour les questions plus complexes, seuls les
templates proches du besoin sont ajoutes au prompt du LLM.

Organisation :

- templates simples : retrouver une equipe, retrouver un joueur, lister les
  joueurs d'une equipe, lister les matchs d'une equipe, recuperer les infos
  custom, lister les tournois et recuperer un vainqueur par id ou par nom ;
- templates complexes : tops, classements, meilleurs joueurs/equipes, matchs de
  tournoi avec vainqueurs.

Les templates de recherche par nom utilisent `LOWER(TRANSLATE(...))` pour
matcher sans tenir compte des majuscules ni des accents.
