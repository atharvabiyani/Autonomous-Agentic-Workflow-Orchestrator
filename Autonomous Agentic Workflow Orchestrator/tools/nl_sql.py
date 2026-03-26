from __future__ import annotations

import json
import os
import re

from tools.read_only_sql import assert_read_only_sql


def _heuristic_nl_to_sql(natural_language: str, tables: list[str], schema_blob: str) -> str:
    """Tiny rule-based fallback when no LLM key is configured."""
    nl = natural_language.lower()
    table = tables[0] if len(tables) == 1 else next((t for t in tables if t.lower() in nl), tables[0] if tables else "")
    if not table:
        msg = "Cannot infer a table name; set OPENAI_API_KEY for NL→SQL or name the table in the instruction."
        raise ValueError(msg)

    col = "value"
    for candidate in ("value", "amount", "price", "score", "total"):
        if candidate in nl:
            col = candidate
            break

    if any(k in nl for k in ("average", "avg", "mean")):
        return f'SELECT AVG("{col}") AS result FROM "{table}"'
    if "sum" in nl:
        return f'SELECT SUM("{col}") AS result FROM "{table}"'
    if "count" in nl:
        return f'SELECT COUNT(*) AS result FROM "{table}"'
    if "min" in nl:
        return f'SELECT MIN("{col}") AS result FROM "{table}"'
    if "max" in nl:
        return f'SELECT MAX("{col}") AS result FROM "{table}"'
    if "all rows" in nl or "all data" in nl or "everything" in nl:
        return f'SELECT * FROM "{table}" LIMIT 500'
    _ = schema_blob
    return f'SELECT * FROM "{table}" LIMIT 100'


async def generate_read_only_sql(natural_language: str, schema_context: str, tables: list[str]) -> str:
    """
    Turn natural language into a single read-only SQL statement.

    Uses OpenAI when ``OPENAI_API_KEY`` is set; otherwise :func:`_heuristic_nl_to_sql`.
    """
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raw = _heuristic_nl_to_sql(natural_language, tables, schema_context)
        return assert_read_only_sql(raw)

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover - optional extra
        msg = "Install openai (pip install openai) or unset OPENAI_API_KEY to use heuristic NL→SQL."
        raise RuntimeError(msg) from exc

    client = AsyncOpenAI(api_key=key)
    system = (
        "You output exactly one SQLite SELECT or WITH query, no markdown fences, no commentary. "
        "The query must be read-only (no INSERT/UPDATE/DELETE/DDL). "
        "Use only tables and columns that appear in the provided schema."
    )
    user = json.dumps(
        {"task": natural_language, "schema": schema_context, "known_tables": tables},
        indent=2,
    )
    resp = await client.chat.completions.create(
        model=os.environ.get("OPENAI_NL_SQL_MODEL", "gpt-4o-mini"),
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    choice = resp.choices[0].message.content
    if not choice:
        msg = "LLM returned empty SQL"
        raise RuntimeError(msg)
    raw = choice.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:sql)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return assert_read_only_sql(raw.strip())
