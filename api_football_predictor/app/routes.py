from fastapi import APIRouter
from pydantic import BaseModel

from app import methods


router = APIRouter()


class CreateCustomTeamRequest(BaseModel):
    team_name: str
    reference_formation: str
    isBudget: bool
    budget: int | None = None
    players: list[int]


class SearchTeamsRequest(BaseModel):
    search: str = ""
    custom: bool = True
    prediction_ready: bool = False
    limit: int = 200


class GetPlayersRequest(BaseModel):
    player_ids: list[int]


class GetTeamsPredictionFeaturesRequest(BaseModel):
    team_ids: list[str]


class CreateTournamentRequest(BaseModel):
    tournament_name: str
    nb_teams: int
    teams: list[str]


class SetTournamentRequest(BaseModel):
    tournament_id: str
    team_id_1: str
    team_id_2: str
    score_team_1: int
    score_team_2: int
    phase: str
    winner_team_id: str | None = None


@router.get("/teams/{search}")
def search_teams(search: str):
    return methods.search_teams(search)


@router.post("/teams")
def get_teams(payload: SearchTeamsRequest):
    return methods.get_teams(payload)


@router.get("/team/{team_id}")
def get_team(team_id: str):
    return methods.get_team(team_id)


@router.get("/team/{team_id}/movements")
def get_team_movements(team_id: int):
    return methods.get_team_movements(team_id)


@router.get("/team/{team_id}/lineup")
def get_team_lineup(team_id: int):
    return methods.get_team_lineup(team_id)


@router.get("/team/{team_id}/prediction_features")
def get_team_prediction_features(team_id: str):
    return methods.get_team_prediction_features(team_id)


@router.post("/teams/prediction_features")
def get_teams_prediction_features(payload: GetTeamsPredictionFeaturesRequest):
    return methods.get_teams_prediction_features(payload)


@router.get("/player/{player_id}")
def get_player(player_id: int):
    return methods.get_player(player_id)


@router.get("/players")
def list_players(line: str | None = None, search: str = "", limit: int = 500):
    return methods.list_players(line=line, search=search, limit=limit)


@router.post("/players")
def get_players(payload: GetPlayersRequest):
    return methods.get_players(payload)


@router.post("/custom/team")
def create_custom_team(payload: CreateCustomTeamRequest):
    return methods.create_custom_team(payload)


@router.post("/custom/tournament")
def create_tournament(payload: CreateTournamentRequest):
    return methods.create_tournament(payload)


@router.get("/custom/tournaments")
def list_tournaments():
    return methods.list_tournaments()


@router.get("/custom/tournament/{tournament_id}")
def get_tournament(tournament_id: str):
    return methods.get_tournament(tournament_id)


@router.post("/custom/tournament/set")
def set_tournament(payload: SetTournamentRequest):
    return methods.set_tournament(payload)
