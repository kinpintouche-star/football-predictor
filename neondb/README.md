# Neon DB data prep

Ce dossier prepare les fichiers utiles pour reconstruire la base Neon de l'API
data, sans lancer de creation de base et sans connexion a Neon.

## Contenu

- `schema.sql` : structure cible des tables Neon.
- `create_tables.py` : cree les tables manquantes depuis `schema.sql`.
- `prepare_neon_db.py` : dry-run qui affiche le SQL qui serait execute.
- `build_tables_from_csv.py` : construit des CSV propres depuis `data/`.
- `data/` : CSV sources utiles au build.
- `build/` : CSV generes, prets a etre charges plus tard.

## CSV sources

Les fichiers sources utilises sont :

- `player-data-full-2025-june.csv`
- `sofifa_team_map.csv`
- `sofifa_team_profiles_enriched.csv`
- `match_outcome_team_ratings.csv`
- `training_match_dataset.csv`

Le CSV `training_match_dataset.csv` est conserve comme reference modele, mais
il n'est pas necessaire pour construire les tables relationnelles de base.

## Ordre de lancement

### 1. Creer les tables vides dans Neon

```bash
python neondb/create_tables.py
```

Cette commande execute `schema.sql`.

Elle cree seulement les tables et index manquants. Elle n'insere aucune donnee.

Les requetes utilisent `CREATE TABLE IF NOT EXISTS` et `CREATE INDEX IF NOT EXISTS` :
elles ne suppriment pas et ne remplacent pas les tables deja presentes.

### 2. Construire les CSV propres

Depuis la racine du projet :

```bash
python neondb/build_tables_from_csv.py
```

Sorties attendues :

- `build/player.csv`
- `build/team.csv`
- `build/match.csv`
- `build/match_team.csv`
- `build/lineup.csv`
- `build/custom_team.csv`
- `build/tournament.csv`
- `build/custom_match.csv`

`lineup.csv` est vide pour le moment, car aucun CSV de compositions n'est
present dans ce dossier.

Les tables custom sont aussi vides au build :

- `custom_team` : equipe creee par l'utilisateur. Son id commence par `c`,
  et elle ajoute `reference_formation` et `budget_eur` aux colonnes d'une team.
- `tournament` : tournoi custom avec nombre d'equipes et vainqueur optionnel.
- `custom_match` : match custom entre deux equipes custom. Son id commence par
  `c` et il peut etre rattache a une phase de tournoi.

### 3. Inserer les CSV dans les tables Neon

Apres avoir genere les CSV avec `build_tables_from_csv.py`, lancer :

```bash
python neondb/load_csv_to_neon.py
```

Le chargement utilise `ON CONFLICT DO NOTHING` :
les lignes deja presentes sont ignorees, pas remplacees.

## Voir le schema sans rien executer

```bash
python neondb/prepare_neon_db.py
```

Ce script affiche le SQL. Il ne se connecte pas a Neon.
