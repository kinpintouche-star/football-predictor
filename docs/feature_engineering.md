# Feature Engineering Joueurs

Ce document resume la methode utilisee dans `neon_to_clusters.ipynb` pour preparer les features avant le clustering des joueurs.

L'objectif est de construire des variables plus claires et moins redondantes que les colonnes Sofifa brutes, sans perdre la logique football.

## Source

Les donnees viennent de la table Neon `player`.

On utilise principalement les attributs Sofifa des joueurs :

- notes techniques, physiques, offensives, defensives et gardien ;
- poste principal : `best_position` ;
- identifiant joueur : `player_id`.

## Decoupage par type de joueur

On separe les joueurs en deux familles, car les variables importantes ne sont pas les memes.

### Joueurs de champ

Postes inclus :

- defenseurs : `CB`, `LB`, `RB`, `LWB`, `RWB` ;
- milieux : `CDM`, `CM`, `CAM`, `LM`, `RM` ;
- attaquants : `ST`, `CF`, `LW`, `RW`.

Features notees sur 100 :

- centres, finition, precision tete, passes courtes, volees ;
- dribble, effet, precision coup franc, passes longues, controle balle ;
- acceleration, vitesse, agilite, reactions, equilibre ;
- puissance frappe, detente, endurance, force, tirs de loin ;
- agressivite, interceptions, placement offensif, vision, penaltys, calme ;
- conscience defensive, tacle, tacle glisse.

Variables de profil conservees a part :

- `skill_moves` ;
- `weak_foot` ;
- `height_cm` ;
- `weight_kg`.

Ces variables ne sont pas moyennees avec les notes 0-100, car elles ne sont pas sur la meme echelle.

Elles ne sont pas automatiquement gardees pour KMeans. On controle d'abord leur correlation avec les features de rating agregees.

`weight_kg` est retire manuellement du clustering, car il est trop redondant avec les dimensions physiques et risque de renforcer artificiellement cet axe.

### Gardiens

Poste inclus :

- `GK`.

Features gardien et style gardien :

- plongeon, jeu a la main, jeu au pied, placement, reflexes ;
- reactions, calme ;
- detente, force, endurance, agressivite ;
- passes courtes, passes longues, vision, controle balle ;
- puissance frappe ;
- acceleration, vitesse, agilite, equilibre.

Variables de profil conservees a part :

- `weak_foot` ;
- `height_cm` ;
- `weight_kg`.

Comme pour les joueurs de champ, ces variables sont controlees avant d'etre utilisees dans KMeans.

`weight_kg` est aussi retire manuellement pour les gardiens.

## Nettoyage

On garde uniquement les joueurs qui ont toutes les features requises pour leur type de poste.

Un joueur de champ doit avoir toutes les features joueurs de champ.

Un gardien doit avoir toutes les features gardien.

Cela evite de creer des clusters bases sur des donnees incompletes ou imputees trop tot.

## Methode d'agregation quantitative

On veut regrouper les features tres liees entre elles.

La methode utilisee est la suivante :

1. calculer la matrice de correlation entre features ;
2. convertir la correlation en distance : `distance = 1 - abs(correlation)` ;
3. faire un clustering hierarchique des colonnes ;
4. couper l'arbre avec `FEATURE_DISTANCE_THRESHOLD = 0.25` ;
5. analyser chaque groupe de features ;
6. moyenner le groupe seulement s'il est suffisamment coherent.

Une distance de `0.25` correspond grossierement a une correlation absolue de `0.75`.

## Regle d'agregation

Un groupe est agrege si :

- il contient au moins deux features ;
- sa correlation absolue moyenne est au moins egale a `0.75`.

Seuil utilise :

```python
MIN_AVG_CORRELATION_TO_AGGREGATE = 0.75
```

Si le groupe est coherent, on cree une nouvelle feature par moyenne.

Exemple logique :

```text
acceleration + sprint_speed -> feature vitesse
standing_tackle + sliding_tackle -> feature tacle
```

Si le groupe n'est pas assez coherent, on garde les features separees.

## Scores controles pour chaque groupe

Pour chaque groupe propose, le notebook calcule :

- `feature_count` : nombre de features dans le groupe ;
- `avg_abs_correlation` : correlation absolue moyenne du groupe ;
- `min_abs_correlation` : correlation minimale dans le groupe ;
- `first_axis_share` : part du premier axe, proche d'une verification type PCA ;
- `should_aggregate` : indique si le groupe doit etre moyenne.

Le but n'est pas d'agreger automatiquement tout ce qui se ressemble un peu, mais seulement les groupes vraiment redondants.

## Controle des variables de profil

Les variables comme `height_cm`, `weight_kg`, `weak_foot` et `skill_moves` peuvent etre utiles, mais elles peuvent aussi etre redondantes avec les ratings.

Exemple : si `weight_kg` est tres correle a une feature physique deja presente, l'ajouter dans KMeans revient a compter deux fois la meme information.

Le notebook calcule donc, pour chaque variable de profil :

- la feature de rating agregee la plus correlee ;
- la correlation absolue maximale ;
- une decision `keep_for_kmeans`.

Seuil utilise :

```python
PROFILE_CORRELATION_THRESHOLD = 0.75
```

Regle :

- si la correlation maximale avec les ratings est inferieure a `0.75`, on garde la variable de profil ;
- sinon, on la retire des features KMeans.

Les decisions sont visibles dans :

```python
profile_control_df
```

Les features finales deviennent donc :

```python
field_absolute_final_columns = field_aggregated_rating_columns + field_selected_profile_columns
gk_absolute_final_columns = gk_aggregated_rating_columns + gk_selected_profile_columns
```

## Features Style-Only

Pour eviter que KMeans separe surtout les joueurs forts des joueurs faibles, le notebook cree aussi des features relatives.

On calcule d'abord le niveau moyen du joueur :

```python
field_level_score = moyenne des features agregees du joueur de champ
gk_level_score = moyenne des features agregees du gardien
```

Puis on calcule les ecarts a ce niveau :

```python
style_feature = feature - level_score
```

Le mode actuel est :

```python
CLUSTERING_FEATURE_MODE = "style"
```

Les colonnes utilisees par KMeans deviennent donc :

```python
field_final_columns = field_style_rating_columns + field_selected_profile_columns
gk_final_columns = gk_style_rating_columns + gk_selected_profile_columns
```

Cette logique conserve les differences de style, mais limite l'effet `joueur fort` vs `joueur faible`.

## Sorties du notebook

Le notebook produit plusieurs objets utiles pour la suite.

### Mapping des aggregations

Pour les joueurs de champ :

```python
field_aggregation_mapping_df
```

Pour les gardiens :

```python
gk_aggregation_mapping_df
```

Ces tables indiquent pour chaque feature finale :

- son nom final ;
- si elle vient d'une moyenne ou d'une feature brute conservee ;
- les features source utilisees.

### Dataset final

Le dataset principal pour la suite est :

```python
players_aggregated_features_df
```

Il contient :

- `player_id` ;
- `best_position` ;
- `position_group` ;
- `position_role` ;
- les variables de profil ;
- les features agregees ;
- les features brutes conservees si elles n'etaient pas assez correlees.

Pour le clustering par role, on utilise :

```python
role_players_aggregated_features_df
```

Cette table conserve les gardiens dans le role `goalkeeper`.

### Features par role

Le dictionnaire suivant prepare le clustering par role :

```python
feature_columns_by_role
```

Mapping utilise :

```python
position_to_role = {
    "GK": "goalkeeper",
    "CB": "central_defender",
    "LB": "fullback_wingback",
    "RB": "fullback_wingback",
    "LWB": "fullback_wingback",
    "RWB": "fullback_wingback",
    "CDM": "defensive_midfielder",
    "CM": "central_midfielder",
    "CAM": "attacking_midfielder",
    "LM": "wide_player",
    "RM": "wide_player",
    "LW": "wide_player",
    "RW": "wide_player",
    "ST": "forward",
    "CF": "forward",
}
```

Le role `goalkeeper` utilise les features gardien.

Tous les autres roles utilisent les features joueurs de champ. Les features gardien ne sont donc pas melangees avec les roles de joueurs de champ.

Le `best_position` reste disponible comme information descriptive, mais le clustering se fait au niveau de `position_role`.

### Nombre de clusters retenu

Les nombres de clusters retenus pour le KMeans final sont :

```python
CLUSTERS_BY_ROLE = {
    "attacking_midfielder": 3,
    "central_defender": 4,
    "central_midfielder": 4,
    "defensive_midfielder": 5,
    "forward": 3,
    "fullback_wingback": 3,
    "goalkeeper": 2,
    "wide_player": 5,
}
```

Ces valeurs sont choisies apres lecture des graphes coude/silhouette et des signatures de profils en mode `style-only`, puis utilisees pour entrainer un KMeans separe par role.

Le notebook permet aussi de challenger ces choix avec `K_CANDIDATES_BY_ROLE`. Pour chaque role et chaque `k` candidat, il affiche :

- la taille des clusters ;
- les postes exacts dominants compares a leur distribution initiale dans le role ;
- les features les plus fortes/faibles par rapport a la moyenne du role ;
- une heatmap des signatures de clusters.

La lecture principale n'est pas le poste exact dominant. Le poste exact est seulement un controle secondaire.

L'objectif principal est de savoir si le cluster a une vraie signature de profil.

Le notebook calcule donc :

- `top_positive_features` : points forts du cluster vs moyenne du role ;
- `top_negative_features` : points faibles du cluster vs moyenne du role ;
- `profile_signal` : intensite moyenne des ecarts principaux ;
- `level_bias` : risque que le cluster soit seulement un axe fort/faible ;
- `same_direction_share` : part des features qui vont dans le meme sens ;
- `profile_read` : lecture synthetique.

Valeurs possibles de `profile_read` :

- `profile_signature` : le cluster a des points forts et points faibles lisibles ;
- `level_axis` : le cluster ressemble surtout a un niveau global fort/faible ;
- `weak_signature` : le cluster n'a pas une signature assez marquee ;
- `mixed_or_level` : lecture ambigue a verifier visuellement.

Pour eviter de surevaluer un poste exact dominant, on compare toujours :

- `cluster_position_share` : part du poste dans le cluster ;
- `role_position_share` : part du poste dans tout le role avant clustering ;
- `overrepresentation_ratio` : `cluster_position_share / role_position_share`.

Un ratio proche de `1` signifie que le poste exact n'est pas particulierement surrepresente.

## Pourquoi cette approche

Cette methode permet de reduire la redondance sans supprimer brutalement de l'information.

On evite que deux variables tres proches comptent deux fois dans les distances du clustering.

Mais on garde les variables separees quand elles ne sont pas assez proches quantitativement.

Cela donne une base plus propre pour la prochaine etape : faire du clustering par role.

## Systeme de styles

Apres le KMeans final, le notebook cree deux tables de lecture :

```python
cluster_style_labels_df
player_role_clusters_with_style_df
```

`cluster_style_labels_df` donne un label lisible pour chaque cluster.

Le label est construit a partir des plus grands ecarts positifs du cluster par rapport a la moyenne de son role.

Exemple :

```text
attaquant - puissance / aerien
joueur de couloir - technique/creation / agilite/equilibre
gardien - taille / arrets
```

Les points faibles du cluster sont conserves dans `style_weaknesses`, pour ne pas surinterpreter le label.

`player_role_clusters_with_style_df` rattache ensuite chaque joueur a son cluster et a son label de style.
