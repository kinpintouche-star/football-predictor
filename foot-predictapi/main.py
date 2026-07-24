import os
from contextlib import asynccontextmanager

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

APP_URI = os.environ.get("APP_URI")
MODEL_ID = os.environ.get("MODEL_ID")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set tracking URI to your Hugging Face application
    mlflow.set_tracking_uri(APP_URI)
    model_uri = f"models:/{MODEL_ID}"
    app.state.model = mlflow.sklearn.load_model(model_uri)
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
    return {"status": "ok", "model_loaded": request.app.state.model is not None}


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
