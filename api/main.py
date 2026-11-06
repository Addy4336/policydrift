"""FastAPI layer over ``policydrift.demo``. It adds no research logic of its own.

Run from the repository root:

    uv run uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from policydrift.demo import DemoService, DemoSettings
from policydrift.llm import LLMError

ROOT = Path(os.environ.get("POLICYDRIFT_ROOT", Path(__file__).resolve().parents[1]))
ORIGINS = os.environ.get("POLICYDRIFT_CORS", "http://localhost:3000,http://127.0.0.1:3000")

app = FastAPI(
    title="PolicyDrift API",
    version="0.1.0",
    description=(
        "Version-aware answers about Indian government rules in English, Hindi and Gujarati, "
        "with validated citations and rule-change flags."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ORIGINS.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def service() -> DemoService:
    model = os.environ.get("POLICYDRIFT_DEMO_MODEL", DemoSettings.model_key)
    return DemoService(ROOT, DemoSettings(model_key=model))


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    language: Literal["en", "hi", "gu"] = "en"
    as_of: date | None = None


@app.get("/api/health")
def health() -> dict[str, object]:
    svc = service()
    return {"status": "ok", "chunks": len(svc.chunks), "model": svc.model_id}


@app.post("/api/ask")
def ask(body: AskRequest) -> dict[str, object]:
    if body.as_of is not None and not date(2015, 1, 1) <= body.as_of <= date(2100, 1, 1):
        raise HTTPException(status_code=422, detail="as_of is out of range")
    try:
        return service().ask(body.question, body.language, body.as_of)
    except LLMError as exc:
        raise HTTPException(
            status_code=503, detail=f"The language model is unavailable: {exc}"
        ) from exc


@app.get("/api/schemes")
def schemes() -> list[dict[str, object]]:
    return service().schemes()


@app.get("/api/examples")
def examples() -> dict[str, list[str]]:
    return service().examples()


@app.get("/api/results")
def results() -> dict[str, str | None]:
    def read(split: str) -> str | None:
        path = ROOT / "paper" / split / "results.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    return {"dev": read("dev") or "", "test": read("test")}
