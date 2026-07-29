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

## Demandes à l'API

Ce que la page « Custom team » ne peut pas faire aujourd'hui, faute
d'endpoint. Convention retenue : **POST avec les filtres dans le payload**,
plutôt que des paramètres d'URL.

Tant que ces endpoints n'existent pas, `api_client` se rabat sur
`players_catalogue.json` et sur la session. Chaque contournement est commenté
à l'endroit concerné.

### 1. Filtre joueur — `POST /players/search`

Remplace le catalogue local. C'est le besoin le plus bloquant : sans lui, on
ne peut composer une équipe qu'avec les 240 joueurs de l'extrait local, sur
les 4203 sélectionnables en base.

```jsonc
// payload
{
  "search": "mbapp",      // filtre texte sur le nom, insensible aux accents
  "line": "FWD",          // GK | DEF | MID | FWD, optionnel
  "montant_max": 50000000,// valeur marchande maximum, optionnel
  "hasscores": true,      // uniquement les joueurs notables
  "limit": 50
}
```

Réponse attendue, par joueur : `player_id`, `player_name`, `best_position`,
`line`, `note`, `price` ( valeur Transfermarkt ), plus le `total` avant
plafonnement pour signaler une liste tronquée.

### 2. Joueurs sans données de score — `POST /players`

Ajouter `hasscores` au payload existant. 1659 joueurs sur 6705 n'ont pas de
profil SoFIFA, donc pas de note calculable, et n'ont rien à faire dans un
sélecteur.

```jsonc
{ "player_ids": [315858], "hasscores": true }
```

### 3. Toutes les équipes — `POST /teams`

Remplace `GET /teams/{search}`, avec un booléen `custom` qui décide si les
équipes custom sont incluses ou si l'on ne renvoie que les vraies.

```jsonc
{ "search": "madrid", "custom": false }
```

Cet endpoint couvre aussi la relecture des équipes custom, que le front ne
sait pas faire : la liste affichée sous le formulaire ne contient que les
équipes créées depuis l'ouverture de la page.

### 4. Suppression d'une équipe custom — `DELETE /custom/team/{id}`

Pas encore arbitré. Le bouton « Retirer » ne fait que masquer l'équipe :
la ligne reste en base.

### 5. Deux échelles de note coexistent

`GET /team/{id}` renvoie `global_note` = `overall_rating`, alors que la note
du modèle est la moyenne des 6 groupes de statistiques de champ. Un gardien
vaut 89 dans le premier cas et 37 dans le second. Une compo pré-remplie par
« Fill » affiche donc des notes sans rapport avec celles du catalogue.
Il faudrait exposer la note du modèle par joueur.

