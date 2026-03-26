from __future__ import annotations

from typing import Any, Protocol

from schema.state import WorkflowGraphState


class InvokableWorkflowGraph(Protocol):
    """Structural type for a compiled LangGraph graph used by FastAPI."""

    def invoke(self, state: WorkflowGraphState, /, **kwargs: Any) -> WorkflowGraphState: ...

    async def ainvoke(self, state: WorkflowGraphState, /, **kwargs: Any) -> WorkflowGraphState: ...
