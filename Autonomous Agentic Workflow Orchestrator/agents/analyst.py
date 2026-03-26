from __future__ import annotations

from typing import Any

from schema.plan import PlanStep
from tools.analyst_tools import run_numpy_reduction


def run_analyst_step(step: PlanStep, artifacts: dict[str, Any]) -> dict[str, Any]:
    """Execute the Analyst agent: NumPy reductions on tabular artifacts."""
    if step.agent != "analyst":
        msg = "run_analyst_step requires agent=analyst"
        raise ValueError(msg)
    source_key = step.input_data_key
    if not source_key:
        msg = "Analyst steps require input_data_key pointing at a tabular artifact."
        raise ValueError(msg)
    raw = artifacts.get(source_key)
    if not isinstance(raw, list):
        msg = f"Artifact {source_key!r} must be a list of row dicts."
        raise TypeError(msg)
    rows: list[dict[str, Any]] = [dict(r) for r in raw]
    column = "value"
    op = step.numpy_op or "mean"
    return run_numpy_reduction(rows, column=column, op=op)
