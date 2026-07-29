from fastapi import FastAPI
from pydantic import BaseModel

from app.methods import chat_with_database
from app.schema import SCHEMA_CONTEXT


app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    max_rows: int = 30


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def get_schema():
    return {"schema": SCHEMA_CONTEXT}


@app.post("/chat")
def chat(payload: ChatRequest):
    return chat_with_database(payload.message, max_rows=payload.max_rows)
