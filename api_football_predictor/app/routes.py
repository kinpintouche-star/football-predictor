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


class GetPlayersRequest(BaseModel):
    player_ids: list[int]


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


@router.get("/teams/{search}")
def search_teams(search: str):
    return methods.search_teams(search)


@router.get("/team/{team_id}")
def get_team(team_id: int):
    return methods.get_team(team_id)


@router.get("/team/{team_id}/movements")
def get_team_movements(team_id: int):
    return methods.get_team_movements(team_id)


@router.get("/team/{team_id}/lineup")
def get_team_lineup(team_id: int):
    return methods.get_team_lineup(team_id)


@router.get("/team/{team_id}/prediction_features")
def get_team_prediction_features(team_id: int):
    return methods.get_team_prediction_features(team_id)


@router.get("/player/{player_id}")
def get_player(player_id: int):
    return methods.get_player(player_id)


@router.post("/players")
def get_players(payload: GetPlayersRequest):
    return methods.get_players(payload)


@router.post("/custom/team")
def create_custom_team(payload: CreateCustomTeamRequest):
    return methods.create_custom_team(payload)


@router.post("/custom/tournament")
def create_tournament(payload: CreateTournamentRequest):
    return methods.create_tournament(payload)


@router.post("/custom/tournament/set")
def set_tournament(payload: SetTournamentRequest):
    return methods.set_tournament(payload)
