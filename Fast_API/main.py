"""Lynceus API. Run from the repo root: uvicorn Fast_API.main:app --reload"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Lynceus")

# Written by pipeline/load.py; resolved from this file so any working directory works
RECORDS = Path(__file__).resolve().parent.parent / "data" / "records.json"


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str


class EmbedResponse(BaseModel):
    embedded: int


def run_agent(question: str) -> str:
    """Feed the question to the agent and return its answer. Not built yet."""
    raise NotImplementedError


def embed_corpus() -> int:
    """Embed the corpus and return how many records were embedded. Not built yet."""
    raise NotImplementedError


@app.exception_handler(NotImplementedError)
def not_implemented(request, exc):
    return JSONResponse(status_code=501, content={"detail": "not implemented yet"})


@app.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    return AskResponse(answer=run_agent(body.question))


@app.post("/embed")
def embed() -> EmbedResponse:
    return EmbedResponse(embedded=embed_corpus())


@app.get("/records")
def records() -> list[dict]:
    if not RECORDS.exists():
        raise HTTPException(404, "data/records.json not found, run pipeline/load.py first")
    return json.loads(RECORDS.read_text(encoding="utf-8"))
