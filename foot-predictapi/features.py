"""Features dérivées des 22 notes de titulaires.

Ce module est partagé par l'entrainement ( scripts/train_local_model.py ) et par
le service d'inférence : le pipeline sérialisé référence `aggregate_team_notes`,
qui doit donc rester importable au même endroit pour être dépicklé.

Pourquoi agréger. Le modèle reçoit 22 notes numérotées par player_id croissant.
Cet ordre n'a aucun sens footballistique : `team_1_player_3_note` désigne un
joueur différent à chaque match. Un arbre qui découpe sur cette colonne apprend
du bruit, ce qui se voyait dans les scores ( forêt aléatoire à 0.454, sous la
référence « toujours domicile » à 0.470 ). En résumant chaque équipe par des
statistiques invariantes à l'ordre, on passe à 0.516.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STARTERS_PER_TEAM = 11

FEATURE_COLUMNS = [
    f"team_{team_number}_player_{player_number}_note"
    for team_number in (1, 2)
    for player_number in range(1, STARTERS_PER_TEAM + 1)
]


def aggregate_team_notes(notes):
    """22 notes brutes -> statistiques par équipe, insensibles à l'ordre."""
    frame = pd.DataFrame(np.asarray(notes, dtype=float), columns=FEATURE_COLUMNS)

    home = frame[FEATURE_COLUMNS[:STARTERS_PER_TEAM]].to_numpy()
    away = frame[FEATURE_COLUMNS[STARTERS_PER_TEAM:]].to_numpy()

    return pd.DataFrame(
        {
            "home_mean": home.mean(axis=1),
            "away_mean": away.mean(axis=1),
            "mean_difference": home.mean(axis=1) - away.mean(axis=1),
            "home_max": home.max(axis=1),
            "away_max": away.max(axis=1),
            "home_std": home.std(axis=1),
            "away_std": away.std(axis=1),
        }
    )
