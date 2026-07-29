ALLOWED_TABLES = {
    "team",
    "player",
    "match",
    "match_team",
    "lineup",
    "custom_team",
    "custom_team_player",
    "tournament",
    "tournament_team",
    "custom_match",
    "custom_lineup",
}


SCHEMA_CONTEXT = """
Tables autorisees en lecture seule.

team(
  team_id, team_name, sofifa_team_id, club_key, uefa_rank,
  club_league_name, overall, attack, midfield, defence,
  build_up_style, defensive_line, defensive_approach
)

player(
  player_id, player_name, full_name, date_of_birth, nationality,
  height_cm, weight_kg, best_position, positions,
  overall_rating, potential, preferred_foot, weak_foot, skill_moves,
  current_club_name, sofifa_value_eur, transfermarkt_market_value_eur,
  has_sofifa_profile,
  crossing, finishing, heading_accuracy, short_passing, volleys,
  dribbling, curve, fk_accuracy, long_passing, ball_control,
  acceleration, sprint_speed, agility, reactions, balance,
  shot_power, jumping, stamina, strength, long_shots,
  aggression, interceptions, attack_position, vision, penalties, composure,
  defensive_awareness, standing_tackle, sliding_tackle,
  gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes
)

match(match_id, match_date, home_score, away_score, result)

match_team(
  match_id, team_id, side, score, coach_name, formation,
  overall, attack, midfield, defence
)

lineup(
  match_id, team_id, player_id, position_player,
  is_starting_match, minute_start, minute_end, minutes_played
)

custom_team(
  custom_team_id, team_name, reference_formation, budget_eur,
  overall, attack, midfield, defence
)

custom_team_player(custom_team_id, player_id)

tournament(tournament_id, tournament_name, nb_teams, winner_team_id)

tournament_team(
  tournament_id, custom_team_id, slot_index, nb_wins, nb_loss, nb_equal
)

custom_match(
  custom_match_id, home_custom_team_id, away_custom_team_id,
  home_score, away_score, result, winner_team_id,
  tournament_phase, tournament_id, created_at
)

custom_lineup(custom_match_id, custom_team_id, player_id, is_starting_match)

Guide de recuperation des donnees.

Joueurs:
- infos, notes, stats et prix: table player;
- prix a utiliser si on parle budget/valeur:
  COALESCE(transfermarkt_market_value_eur, sofifa_value_eur);
- joueurs sans profil SoFIFA: has_sofifa_profile = 0 ou NULL;
- joueurs utilisables pour statistiques SoFIFA: has_sofifa_profile = 1.

Equipes reelles:
- infos generales et notes d'equipe: team;
- chercher une equipe par nom: team.team_name;
- effectif observe par les matchs: lineup JOIN match JOIN player;
- dernier onze d'une equipe: prendre le match le plus recent dans lineup/match,
  puis is_starting_match = 1.

Equipes custom:
- infos generales et notes: custom_team;
- joueurs d'une equipe custom: custom_team_player JOIN player;
- budget d'une equipe custom: sommer les prix des joueurs.

Matchs reels:
- date et score: match;
- equipes, cote domicile/exterieur, coach, formation et notes d'equipe au match:
  match_team;
- joueurs, postes et temps de jeu: lineup;
- pour afficher un match complet: match JOIN match_team JOIN lineup JOIN player.

Tournois:
- tournoi: tournament;
- equipes inscrites et ordre dans le tableau: tournament_team.slot_index;
- matchs joues: custom_match;
- joueurs alignes dans un match custom: custom_lineup JOIN player;
- vainqueur d'un match custom: custom_match.winner_team_id si present,
  sinon le deduire avec home_score et away_score.

Regles SQL utiles:
- pour chercher par nom de joueur/equipe/tournoi, utiliser la logique des
  templates `*_by_name.sql` avec LOWER(TRANSLATE(...)) plutot qu'un simple ILIKE;
- si la question demande "la meilleure equipe" sans autre precision:
  utiliser team.uefa_rank ASC;
- si la question demande "l'equipe la mieux notee" ou "par overall":
  utiliser team.overall DESC;
- si la question demande "la meilleure equipe custom":
  utiliser custom_team.overall DESC;
- utiliser LEFT JOIN seulement quand l'information peut manquer;
- exclure les NULL quand on classe par note, prix, taille ou autre metrique;
- utiliser NULLS LAST dans les classements;
- utiliser LIMIT quand la question demande un top ou une liste courte;
- ne jamais inventer une colonne: si elle n'est pas dans le schema, la calculer
  avec les tables ci-dessus ou expliquer que ce n'est pas disponible.
"""
