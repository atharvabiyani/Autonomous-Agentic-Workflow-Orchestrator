from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired

from typing_extensions import TypedDict

from schema.plan import PlanStep, WorkflowStatus


def _merge_artifacts(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, Any]:
    """Reducer for LangGraph: shallow-merge artifact dictionaries."""
    base: dict[str, Any] = {} if left is None else dict(left)
    if right:
        base.update(right)
    return base


class WorkflowGraphState(TypedDict, total=False):
    """LangGraph state: strictly typed fields the orchestrator reads and writes."""

    goal: str
    plan: list[PlanStep]
    current_step_index: int
    artifacts: Annotated[dict[str, Any], _merge_artifacts]
    verification_notes: Annotated[list[str], operator.add]
    status: WorkflowStatus
    error: NotRequired[str | None]
