"""Postgres (Supabase) connection and migration runner for the demo store."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import psycopg

from policydrift.ingest.build import Chunk


def read_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines; ignores blanks and comments. Never logs values."""
    values: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def database_url(root: Path) -> str:
    url = os.environ.get("SUPABASE_DB_URL") or read_env_file(root / ".env").get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("SUPABASE_DB_URL is not set (see .env.example)")
    return url


def connect(root: Path) -> psycopg.Connection:
    return psycopg.connect(database_url(root), connect_timeout=15)


CHUNK_COLUMNS = [
    "chunk_id",
    "scheme",
    "version",
    "effective_from",
    "effective_to",
    "announced_on",
    "language",
    "source_url",
    "source_path",
    "source_sha256",
    "source_release_id",
    "ministry",
    "title",
    "posted_on",
    "chunk_index",
    "raw_start",
    "raw_end",
    "text",
]


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


def upload_chunks(
    conn: psycopg.Connection,
    chunks: Sequence[Chunk],
    vectors: Sequence[Sequence[float]],
    model_key: str,
) -> int:
    """Upsert chunks with their embeddings. Idempotent: reruns overwrite the same rows."""
    cols = ", ".join([*CHUNK_COLUMNS, "embedding", "embedding_model"])
    marks = ", ".join(["%s"] * len(CHUNK_COLUMNS)) + ", %s::vector, %s"
    updates = ", ".join(
        f"{c} = excluded.{c}" for c in [*CHUNK_COLUMNS[1:], "embedding", "embedding_model"]
    )
    sql = (
        f"insert into public.chunks ({cols}) values ({marks}) "
        f"on conflict (chunk_id) do update set {updates}"
    )
    with conn.transaction(), conn.cursor() as cur:
        for chunk, vector in zip(chunks, vectors, strict=True):
            row = chunk.model_dump()
            cur.execute(
                sql,
                [row[c] for c in CHUNK_COLUMNS] + [vector_literal(vector), model_key],
            )
    return len(chunks)


def apply_migrations(conn: psycopg.Connection, migrations_dir: Path) -> list[str]:
    """Apply each ``*.sql`` file once, in name order. Returns the names applied this run."""
    applied: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            "create table if not exists public.schema_migrations "
            "(name text primary key, applied_at timestamptz not null default now())"
        )
        cur.execute("select name from public.schema_migrations")
        done = {row[0] for row in cur.fetchall()}
    conn.commit()
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        if sql_file.name in done:
            continue
        with conn.transaction(), conn.cursor() as cur:
            cur.execute(sql_file.read_text(encoding="utf-8"))
            cur.execute("insert into public.schema_migrations (name) values (%s)", (sql_file.name,))
        applied.append(sql_file.name)
    return applied
