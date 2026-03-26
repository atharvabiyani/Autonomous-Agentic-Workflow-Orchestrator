from __future__ import annotations

import re

# Disallow obvious write / DDL tokens (best-effort; DB authorizer is the real guard).
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|VACUUM|TRUNCATE)\b",
    re.IGNORECASE | re.DOTALL,
)


def assert_read_only_sql(sql: str) -> str:
    """
    Validate that SQL looks read-only before sending to MCP ``read_query``.

    The SQLite MCP server also enforces read-only via ``set_authorizer``.
    """
    text = sql.strip().rstrip(";").strip()
    if not text:
        msg = "SQL query is empty"
        raise ValueError(msg)
    head = text.lstrip("(").lstrip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        msg = "Only SELECT or WITH statements are allowed."
        raise ValueError(msg)
    if _FORBIDDEN.search(text):
        msg = "Query contains forbidden non-read-only keywords."
        raise ValueError(msg)
    return text
