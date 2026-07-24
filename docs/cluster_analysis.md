# Analyse Des Clusters

Analyse executee depuis `neon_to_clusters.ipynb`.

## Donnees Utilisees

- joueurs charges : 6 705 ;
- joueurs conserves apres nettoyage : 5 023 ;
- joueurs de champ : 4 518 ;
- gardiens : 505.

Les resultats exportes sont dans `analysis_outputs/`.

## Decision Actuelle

On utilise maintenant une logique `style-only`.

Au lieu de clusteriser directement les notes absolues, on calcule d'abord le niveau moyen du joueur, puis on regarde ses ecarts relatifs.

Exemple :

```text
style_vitesse = vitesse - niveau_moyen_du_joueur
style_passe = passe - niveau_moyen_du_joueur
```

Cela retire une grande partie de l'effet `joueur fort` vs `joueur faible`.

Le clustering travaille donc davantage sur la forme du profil :

- rapide mais peu physique ;
- createur mais peu defensif ;
- puissant mais moins technique ;
- gardien fort en reflexes mais moins propre au pied.

## Variables Retirees

`weight_kg` est retire manuellement des features KMeans.

Raison : le poids est souvent redondant avec la force, le physique ou certains profils defensifs. Le garder risquait de compter deux fois la meme information.

Les variables de profil encore disponibles pour KMeans sont controlees par correlation :

- joueurs de champ : `skill_moves`, `weak_foot` ;
- gardiens : `weak_foot`, `height_cm`.

## Lecture Des Clusters

Un cluster `profile_signature` signifie que le groupe a des points forts et faibles distincts.

Un cluster `mixed_or_level` signifie que la lecture est encore ambigue.

Un cluster `level_axis` signifie que le cluster ressemble surtout a un niveau global fort/faible. C'est ce que l'approche `style-only` cherche a eviter.

## Resultat Du Run Style-Only

Le changement est net : les clusters deviennent beaucoup plus interpretes comme des profils.

Avec les valeurs actuelles de `CLUSTERS_BY_ROLE`, les 29 clusters finaux sont classes `profile_signature`.

| role | k actuel | lecture |
|---|---:|---|
| attacking_midfielder | 3 | bon, les 3 clusters ont une signature |
| central_defender | 4 | bon, les 4 clusters ont une signature |
| central_midfielder | 4 | bon, les 4 clusters ont une signature |
| defensive_midfielder | 5 | bon, les 5 clusters ont une signature |
| forward | 3 | bon, les 3 clusters ont une signature |
| fullback_wingback | 3 | bon, les 3 clusters ont une signature |
| goalkeeper | 2 | bon compromis simple |
| wide_player | 5 | bon, les 5 clusters ont une signature |

## Recommandation

Je garderais l'approche `style-only` comme base principale.

Je mettrais a jour les clusters finaux comme suit :

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

`attacking_midfielder = 4` reste une option si l'on veut plus de finesse, mais `3` est deja lisible.

## Pourquoi C'est Mieux

L'ancienne version travaillait trop sur les notes absolues. Beaucoup de features montaient ensemble, donc KMeans retrouvait souvent :

- joueurs forts ;
- joueurs moyens ;
- joueurs faibles.

La version `style-only` met tous les joueurs sur une base plus comparable.

Un tres bon joueur et un joueur moyen peuvent donc etre proches s'ils ont le meme style relatif, ce qui est exactement ce qu'on veut pour construire des profils.

## Systeme De Styles

Le notebook cree maintenant une table de labels lisibles :

```python
cluster_style_labels_df
```

Pour chaque role, on peut prendre les features les plus positives et negatives du centre de cluster, puis produire un label humain :

- `forward_0` -> attaquant - puissance / aerien ;
- `forward_2` -> attaquant - centre/effet / technique/creation ;
- `wide_player_0` -> joueur de couloir - technique/creation / agilite/equilibre ;
- `goalkeeper_0` -> gardien - taille / arrets ;
- `goalkeeper_1` -> gardien - equilibre / agilite.

Ces labels sont plus utiles que des numeros de clusters pour la suite du modele.

Une seconde table rattache chaque joueur a son cluster et a son label :

```python
player_role_clusters_with_style_df
```
