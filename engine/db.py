"""Postgres access — one async pool, event append, thin query helpers."""
import json
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool

from engine.config import settings

pool = AsyncConnectionPool(settings.database_url, open=False, kwargs={"row_factory": dict_row})


async def open_pool() -> None:
    await pool.open()


async def close_pool() -> None:
    await pool.close()


async def fetch_all(query: str, *args: Any) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(query, args)
        return await cur.fetchall()


async def fetch_one(query: str, *args: Any) -> dict | None:
    async with pool.connection() as conn:
        cur = await conn.execute(query, args)
        return await cur.fetchone()


async def execute(query: str, *args: Any) -> None:
    async with pool.connection() as conn:
        await conn.execute(query, args)


async def append_event(
    conn: Any,
    *,
    actor: str,
    event_type: str,
    company_id: UUID | None = None,
    work_item_id: UUID | None = None,
    correlation_id: UUID | None = None,
    source: str = "engine",
    payload: dict | None = None,
    policy_decision: dict | None = None,
    provenance: dict | None = None,
) -> dict:
    """Append to the immutable log. Caller passes its open connection so the
    event lands in the same transaction as the projection update."""
    cur = await conn.execute(
        """
        INSERT INTO event (company_id, actor, event_type, work_item_id,
                           correlation_id, source, payload, policy_decision, provenance)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING event_id, created_at
        """,
        (
            company_id, actor, event_type, work_item_id, correlation_id, source,
            Json(payload or {}),
            Json(policy_decision) if policy_decision else None,
            Json(provenance) if provenance else None,
        ),
    )
    return await cur.fetchone()


def as_json(row: dict) -> dict:
    """Make a DB row JSON-serializable (UUID/datetime to str)."""
    return json.loads(json.dumps(row, default=str))
