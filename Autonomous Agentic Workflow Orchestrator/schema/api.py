from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schema.plan import PlanStep, WorkflowStatus


class RunWorkflowRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="High-level objective for the Manager.")
    plan_override: list[PlanStep] | None = Field(
        default=None,
        description="Optional explicit plan; when set, the Manager skips heuristic planning.",
    )


class RunWorkflowResponse(BaseModel):
    status: WorkflowStatus
    plan: list[PlanStep]
    artifacts: dict[str, Any]
    verification_notes: list[str]
    error: str | None = None


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "agentic-workflow-orchestrator"
