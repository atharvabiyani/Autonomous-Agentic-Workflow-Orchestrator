from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import psycopg
from psycopg.rows import dict_row
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """Direct Postgres DSN for development or when MCP forwards to the same database."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")

    dsn: str | None = None


@runtime_checkable
class PostgresQueryClient(Protocol):
    """Contract for any Postgres-backed client (MCP implementation or direct psycopg)."""

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute read-oriented SQL and return row dicts."""
        ...


class StubPostgresMCPClient:
    """
    In-memory stand-in for an MCP Postgres tool.

    Wire a real MCP server (e.g. official Postgres MCP) by implementing
    :class:`PostgresQueryClient` and delegating ``query`` to the MCP tool call.
    """

    def query(self, sql: str) -> list[dict[str, Any]]:
        _ = sql
        return [
            {"id": 1, "value": 10.0, "region": "east"},
            {"id": 2, "value": 20.0, "region": "west"},
            {"id": 3, "value": 30.0, "region": "east"},
        ]


class DirectPsycopgPostgresClient:
    """Optional direct DB access using the same interface as the MCP tool would expose."""

    def __init__(self, dsn: str) -> None:
        self._dsn: str = dsn

    def query(self, sql: str) -> list[dict[str, Any]]:
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                rows: list[Any] = cur.fetchall()
        return [dict(r) for r in rows]


def build_postgres_client() -> PostgresQueryClient:
    """Prefer real DSN when configured; otherwise deterministic stub for local demos."""
    settings = PostgresSettings()
    if settings.dsn:
        return DirectPsycopgPostgresClient(settings.dsn)
    return StubPostgresMCPClient()
