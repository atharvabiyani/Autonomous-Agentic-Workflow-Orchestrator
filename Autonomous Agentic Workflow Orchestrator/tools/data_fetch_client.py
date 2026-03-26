from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AsyncDataFetchClient(Protocol):
    """Async tabular data access (MCP SQLite or in-process stub)."""

    async def list_tables(self) -> list[str]:
        """Return user table names."""
        ...

    async def get_table_schema(self, table_name: str) -> str:
        """Schema text/JSON for NL→SQL context."""
        ...

    async def read_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute read-only SQL; return JSON-serializable rows."""
        ...


class StubAsyncDataFetchClient:
    """Used when ``SQLITE_DB_PATH`` is unset (CI / quick demos without MCP)."""

    async def list_tables(self) -> list[str]:
        return ["demo_metrics"]

    async def get_table_schema(self, table_name: str) -> str:
        _ = table_name
        return '{"table":"demo_metrics","columns":[{"name":"id"},{"name":"value"},{"name":"region"}]}'

    async def read_query(self, sql: str) -> list[dict[str, Any]]:
        _ = sql
        return [
            {"id": 1, "value": 10.0, "region": "east"},
            {"id": 2, "value": 20.0, "region": "west"},
            {"id": 3, "value": 30.0, "region": "east"},
        ]
