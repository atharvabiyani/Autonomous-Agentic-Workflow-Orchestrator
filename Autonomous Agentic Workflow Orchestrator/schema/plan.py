from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["data_fetcher", "analyst"]
NumpyOp = Literal["mean", "sum", "std", "min", "max"]
WorkflowStatus = Literal["planning", "executing", "verifying", "done", "failed"]


class PlanStep(BaseModel):
    """Single delegated unit of work for a sub-agent."""

    step_id: str = Field(..., description="Stable id for logging and verification.")
    agent: AgentName
    instruction: str = Field(..., description="Natural-language intent for the sub-agent.")
    sql: str | None = Field(
        default=None,
        description="Optional SQL for the Data-Fetcher when agent is data_fetcher.",
    )
    data_key: str = Field(
        ...,
        description="Key under which this step's primary artifact is stored in state.artifacts.",
    )
    input_data_key: str | None = Field(
        default=None,
        description="For analyst steps: artifact key produced by a prior fetch/analyze step.",
    )
    numpy_op: NumpyOp | None = Field(
        default=None,
        description="When agent is analyst, which reduction to apply to numeric columns.",
    )


class VerificationResult(BaseModel):
    ok: bool
    notes: list[str] = Field(default_factory=list)
