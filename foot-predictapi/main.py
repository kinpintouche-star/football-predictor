import os
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

APP_URI = os.environ.get("APP_URI")
MODEL_ID = os.environ.get("MODEL_ID")

# Deux façons de charger le modèle :
#
# * MLflow, dès que APP_URI et MODEL_ID sont fournis. C'est la voie visée en
#   production, mais elle suppose un modèle enregistré dans le registry ;
# * un fichier joblib local, produit par scripts/train_local_model.py. C'est la
#   voie par défaut, qui permet de faire tourner le service sans MLflow.
#
# Le contrat de /predict est identique dans les deux cas : 22 notes en entrée,
# une classe dans {-1, 0, 1} en sortie.
DEFAULT_LOCAL_MODEL_PATH = Path(__file__).parent / "model" / "match_outcome.joblib"
LOCAL_MODEL_PATH = Path(os.environ.get("LOCAL_MODEL_PATH", DEFAULT_LOCAL_MODEL_PATH))


def load_model():
    if APP_URI and MODEL_ID:
        import mlflow

        mlflow.set_tracking_uri(APP_URI)
        return mlflow.sklearn.load_model(f"models:/{MODEL_ID}"), f"mlflow:{MODEL_ID}"

    if LOCAL_MODEL_PATH.is_file():
        import joblib

        return joblib.load(LOCAL_MODEL_PATH), f"local:{LOCAL_MODEL_PATH.name}"

    raise RuntimeError(
        "Aucun modèle disponible : renseignez APP_URI et MODEL_ID, ou lancez "
        "python scripts/train_local_model.py pour produire un modèle local."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model, app.state.model_source = load_model()
    yield


app = FastAPI(title="FootBall Team Match Predictions", lifespan=lifespan)


class FootBallTeamFeatures(BaseModel):
    team_1_player_1_note: float = Field(..., gt=0, description="Note du joueur 1 de l'équipe 1")
    team_1_player_2_note: float = Field(..., gt=0, description="Note du joueur 2 de l'équipe 1")
    team_1_player_3_note: float = Field(..., gt=0, description="Note du joueur 3 de l'équipe 1")
    team_1_player_4_note: float = Field(..., gt=0, description="Note du joueur 4 de l'équipe 1")
    team_1_player_5_note: float = Field(..., gt=0, description="Note du joueur 5 de l'équipe 1")
    team_1_player_6_note: float = Field(..., gt=0, description="Note du joueur 6 de l'équipe 1")
    team_1_player_7_note: float = Field(..., gt=0, description="Note du joueur 7 de l'équipe 1")
    team_1_player_8_note: float = Field(..., gt=0, description="Note du joueur 8 de l'équipe 1")
    team_1_player_9_note: float = Field(..., gt=0, description="Note du joueur 9 de l'équipe 1")
    team_1_player_10_note: float = Field(..., gt=0, description="Note du joueur 10 de l'équipe 1")
    team_1_player_11_note: float = Field(..., gt=0, description="Note du joueur 11 de l'équipe 1")
    team_2_player_1_note: float = Field(..., gt=0, description="Note du joueur 1 de l'équipe 2")
    team_2_player_2_note: float = Field(..., gt=0, description="Note du joueur 2 de l'équipe 2")
    team_2_player_3_note: float = Field(..., gt=0, description="Note du joueur 3 de l'équipe 2")
    team_2_player_4_note: float = Field(..., gt=0, description="Note du joueur 4 de l'équipe 2")
    team_2_player_5_note: float = Field(..., gt=0, description="Note du joueur 5 de l'équipe 2")
    team_2_player_6_note: float = Field(..., gt=0, description="Note du joueur 6 de l'équipe 2")
    team_2_player_7_note: float = Field(..., gt=0, description="Note du joueur 7 de l'équipe 2")
    team_2_player_8_note: float = Field(..., gt=0, description="Note du joueur 8 de l'équipe 2")
    team_2_player_9_note: float = Field(..., gt=0, description="Note du joueur 9 de l'équipe 2")
    team_2_player_10_note: float = Field(..., gt=0, description="Note du joueur 10 de l'équipe 2")
    team_2_player_11_note: float = Field(..., gt=0, description="Note du joueur 11 de l'équipe 2")

class PredictionResponse(BaseModel):
    match_score_predict: int


@app.get("/health")
def health(request: Request):
    return {
        "status": "ok",
        "model_loaded": request.app.state.model is not None,
        "model_source": getattr(request.app.state, "model_source", None),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict(features: FootBallTeamFeatures):
    model = app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail="Modele non charge")

    input_df = pd.DataFrame(
        [
            {
                "team_1_player_1_note": features.team_1_player_1_note,
                "team_1_player_2_note": features.team_1_player_2_note,
                "team_1_player_3_note": features.team_1_player_3_note,
                "team_1_player_4_note": features.team_1_player_4_note,
                "team_1_player_5_note": features.team_1_player_5_note,
                "team_1_player_6_note": features.team_1_player_6_note,
                "team_1_player_7_note": features.team_1_player_7_note,
                "team_1_player_8_note": features.team_1_player_8_note,
                "team_1_player_9_note": features.team_1_player_9_note,
                "team_1_player_10_note": features.team_1_player_10_note,
                "team_1_player_11_note": features.team_1_player_11_note,
                "team_2_player_1_note": features.team_2_player_1_note,
                "team_2_player_2_note": features.team_2_player_2_note,
                "team_2_player_3_note": features.team_2_player_3_note,
                "team_2_player_4_note": features.team_2_player_4_note,
                "team_2_player_5_note": features.team_2_player_5_note,
                "team_2_player_6_note": features.team_2_player_6_note,
                "team_2_player_7_note": features.team_2_player_7_note,
                "team_2_player_8_note": features.team_2_player_8_note,
                "team_2_player_9_note": features.team_2_player_9_note,
                "team_2_player_10_note": features.team_2_player_10_note,
                "team_2_player_11_note": features.team_2_player_11_note,
            }
        ]
    )

    prediction = model.predict(input_df)
    match_predict = int(prediction[0])

    if match_predict not in [-1, 0, 1]:
        raise HTTPException(status_code=500, detail=f"Invalid match prediction: {match_predict}")

    return PredictionResponse(match_score_predict=match_predict)
