from __future__ import annotations

import json
from typing import Any, cast

from mcp.types import CallToolResult, TextContent


def call_tool_result_to_json(result: CallToolResult) -> Any:
    """Normalize MCP ``call_tool`` payloads to Python JSON values."""
    if result.structuredContent is not None:
        return result.structuredContent
    if not result.content:
        return None
    block = result.content[0]
    if isinstance(block, TextContent):
        text = block.text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return cast(Any, block)
