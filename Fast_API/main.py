"""Lynceus API. Run from the repo root: uvicorn Fast_API.main:app --reload"""
import json
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from Fast_API.agent import run_agent

app = FastAPI(title="Lynceus")

# Written by pipeline/load.py; resolved from this file so any working directory works
RECORDS = Path(__file__).resolve().parent.parent / "data" / "records.json"


class AskRequest(BaseModel):
    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[dict] = []  # the top 3 search hits the answer is based on


class EmbedResponse(BaseModel):
    embedded: int


def embed_corpus() -> int:
    """Embed the corpus and return how many records were embedded. Not built yet."""
    raise NotImplementedError

@app.get("/health") 
def health():
    return{"status": "Ok"}

@app.exception_handler(NotImplementedError)
def not_implemented(request, exc):
    return JSONResponse(status_code=501, content={"detail": "not implemented yet"})


@app.exception_handler(anthropic.AnthropicError)
def claude_failed(request, exc):
    # Missing API key, outage, rate limit: show the reason instead of a bare 500
    return JSONResponse(status_code=502, content={"detail": f"Claude API error: {exc}"})


@app.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    return AskResponse(**run_agent(body.question))


@app.post("/embed")
def embed() -> EmbedResponse:
    return EmbedResponse(embedded=embed_corpus())


@app.get("/records")
def records() -> list[dict]:
    if not RECORDS.exists():
        raise HTTPException(404, "data/records.json not found, run pipeline/load.py first")
    return json.loads(RECORDS.read_text(encoding="utf-8"))


@app.get("/records/{case_id}")
def record(case_id: str) -> dict:
    for r in records():
        if r["case_id"] == case_id:
            return r
    raise HTTPException(404, f"no record with case_id '{case_id}'")
