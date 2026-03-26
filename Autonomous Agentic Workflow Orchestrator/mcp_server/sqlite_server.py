"""
SQLite MCP server (stdio) following the Model Context Protocol Python SDK.

Exposes read-only tools aligned with common SQLite MCP servers:
``list_tables``, ``get_table_schema``, ``read_query``.

Run (typically spawned by the app client, not manually):
    SQLITE_MCP_DB_PATH=/path/to.db python -m mcp_server.sqlite_server

See: https://modelcontextprotocol.io/ and the ``mcp`` Python SDK.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

_DB_PATH: Path | None = None
mcp = FastMCP("SQLite (read-only)", json_response=True)


def _db_path() -> Path:
    if _DB_PATH is None:
        msg = "SQLITE_MCP_DB_PATH is not set"
        raise RuntimeError(msg)
    return _DB_PATH


def _readonly_connection() -> sqlite3.Connection:
    path = _db_path()
    uri = path.resolve().as_uri()
    conn = sqlite3.connect(f"{uri}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    def _authorizer(
        action: int,
        _p1: str | None,
        _p2: str | None,
        _p3: str | None,
        _p4: str | None,
    ) -> int:
        # Allow reads and SQLite functions used by SELECT; deny mutations.
        allowed = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
        }
        if action in allowed:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    conn.set_authorizer(_authorizer)
    return conn


@mcp.tool()
def list_tables() -> list[str]:
    """List all non-system tables in the connected SQLite database."""
    with _readonly_connection() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [str(r[0]) for r in cur.fetchall()]


@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """Return CREATE TABLE SQL and a short column summary for schema-aware query generation."""
    if not table_name.replace("_", "").isalnum():
        msg = "Invalid table name"
        raise ValueError(msg)
    with _readonly_connection() as conn:
        cur = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        row = cur.fetchone()
        if row is None or row[0] is None:
            msg = f"Unknown table: {table_name}"
            raise ValueError(msg)
        create_sql = str(row[0])
        info = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        cols: list[dict[str, Any]] = []
        for r in info:
            cols.append(
                {
                    "cid": r[0],
                    "name": r[1],
                    "type": r[2],
                    "notnull": r[3],
                    "dflt_value": r[4],
                    "pk": r[5],
                }
            )
        return json.dumps({"create_sql": create_sql, "columns": cols}, indent=2)


@mcp.tool()
def read_query(query: str) -> list[dict[str, Any]]:
    """
    Execute a read-only SQL query (SELECT / WITH). Mutating statements are blocked
    by SQLite authorizer on the connection.
    """
    q = query.strip().rstrip(";")
    upper = q.lstrip().upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        msg = "Only SELECT or WITH queries are allowed."
        raise ValueError(msg)
    with _readonly_connection() as conn:
        cur = conn.execute(q)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def main() -> None:
    global _DB_PATH
    env_path = os.environ.get("SQLITE_MCP_DB_PATH")
    if env_path:
        _DB_PATH = Path(env_path)
    elif len(sys.argv) >= 2:
        _DB_PATH = Path(sys.argv[1])
    else:
        print("Usage: SQLITE_MCP_DB_PATH=/path/to.db python -m mcp_server.sqlite_server", file=sys.stderr)
        sys.exit(1)
    if not _DB_PATH.is_file():
        print(f"SQLite file not found: {_DB_PATH}", file=sys.stderr)
        sys.exit(1)
    mcp.run()


if __name__ == "__main__":
    main()
