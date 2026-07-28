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
  tournament_id, custom_team_id, nb_wins, nb_loss, nb_equal
)

custom_match(
  custom_match_id, home_custom_team_id, away_custom_team_id,
  home_score, away_score, result, tournament_phase, tournament_id
)

custom_lineup(custom_match_id, custom_team_id, player_id, is_starting_match)
"""
