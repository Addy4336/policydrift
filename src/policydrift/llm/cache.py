"""On-disk response cache (SQLite) keyed by the request hash."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from policydrift.llm.types import LLMRequest, LLMResponse


class ResponseCache:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS responses "
            "(key TEXT PRIMARY KEY, request TEXT NOT NULL, response TEXT NOT NULL)"
        )
        self._db.commit()

    def get(self, request: LLMRequest) -> LLMResponse | None:
        row = self._db.execute(
            "SELECT response FROM responses WHERE key = ?", (request.cache_key(),)
        ).fetchone()
        if row is None:
            return None
        return LLMResponse.model_validate_json(row[0]).model_copy(update={"cached": True})

    def put(self, request: LLMRequest, response: LLMResponse) -> None:
        stored = response.model_copy(update={"cached": False})
        self._db.execute(
            "INSERT OR REPLACE INTO responses (key, request, response) VALUES (?, ?, ?)",
            (request.cache_key(), request.model_dump_json(), stored.model_dump_json()),
        )
        self._db.commit()

    def __len__(self) -> int:
        row = self._db.execute("SELECT COUNT(*) FROM responses").fetchone()
        return int(row[0])

    def close(self) -> None:
        self._db.close()
