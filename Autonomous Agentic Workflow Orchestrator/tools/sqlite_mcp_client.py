from __future__ import annotations

import json
from typing import Any

from mcp import ClientSession

from tools.mcp_tool_parse import call_tool_result_to_json
from tools.read_only_sql import assert_read_only_sql


class McpSqliteDataFetchClient:
    """
    MCP client for the local :mod:`mcp_server.sqlite_server` tools.

    Follows the stdio client pattern from https://modelcontextprotocol.io/quickstart/client
    (``ClientSession`` + ``call_tool``).
    """

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def list_tables(self) -> list[str]:
        result = await self._session.call_tool("list_tables", arguments={})
        payload = call_tool_result_to_json(result)
        if not isinstance(payload, list):
            msg = f"list_tables: unexpected payload: {payload!r}"
            raise TypeError(msg)
        return [str(x) for x in payload]

    async def get_table_schema(self, table_name: str) -> str:
        result = await self._session.call_tool(
            "get_table_schema",
            arguments={"table_name": table_name},
        )
        payload = call_tool_result_to_json(result)
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, indent=2, default=str)

    async def read_query(self, sql: str) -> list[dict[str, Any]]:
        safe = assert_read_only_sql(sql)
        result = await self._session.call_tool(
            "read_query",
            arguments={"query": safe},
        )
        payload = call_tool_result_to_json(result)
        if payload is None:
            return []
        if not isinstance(payload, list):
            msg = f"read_query: expected list of rows, got {type(payload)}"
            raise TypeError(msg)
        return [dict(r) for r in payload]
