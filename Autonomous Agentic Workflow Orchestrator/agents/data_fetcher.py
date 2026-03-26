from __future__ import annotations

from typing import Any

from schema.plan import PlanStep
from tools.data_fetch_client import AsyncDataFetchClient
from tools.nl_sql import generate_read_only_sql
from tools.read_only_sql import assert_read_only_sql


async def run_data_fetcher_step_async(
    step: PlanStep,
    client: AsyncDataFetchClient,
) -> list[dict[str, Any]]:
    """
    Data-Fetcher: list schema via MCP, optionally NL→read-only SQL, execute via MCP, return rows.

    When ``step.sql`` is set, NL generation is skipped and the statement is still validated
    as read-only before execution.
    """
    if step.agent != "data_fetcher":
        msg = "run_data_fetcher_step_async requires agent=data_fetcher"
        raise ValueError(msg)

    if step.sql is not None and step.sql.strip():
        safe_sql = assert_read_only_sql(step.sql)
        return await client.read_query(safe_sql)

    tables = await client.list_tables()
    if not tables:
        msg = "Database has no user tables to query."
        raise RuntimeError(msg)

    schema_parts: list[str] = []
    for name in tables[:8]:
        schema_parts.append(await client.get_table_schema(name))
    schema_context = "\n\n".join(schema_parts)

    sql = await generate_read_only_sql(
        natural_language=step.instruction,
        schema_context=schema_context,
        tables=tables,
    )
    return await client.read_query(sql)
