from __future__ import annotations

import re
from typing import Any

from agents.base_manager import BaseManager
from schema.plan import NumpyOp, PlanStep, VerificationResult


class HeuristicManager(BaseManager):
    """
    Deterministic Manager for demos and tests (no LLM key required).

    Replace with an LLM-backed planner that emits validated :class:`PlanStep` models
    when you are ready for autonomous natural-language planning.
    """

    def plan(self, goal: str, context: dict[str, Any]) -> list[PlanStep]:
        _ = context
        g = goal.lower()
        wants_fetch = any(
            token in g
            for token in (
                "fetch",
                "postgres",
                "database",
                "sql",
                "select",
                "query",
                "table",
            )
        )
        wants_analyst = any(
            token in g
            for token in (
                "mean",
                "average",
                "numpy",
                "analyze",
                "analysis",
                "sum",
                "std",
                "min",
                "max",
            )
        )

        op_match = re.search(r"\b(mean|average|sum|std|min|max)\b", g)
        numpy_op: NumpyOp = "mean"
        if op_match:
            mapped = op_match.group(1)
            if mapped == "average":
                numpy_op = "mean"
            elif mapped in ("mean", "sum", "std", "min", "max"):
                numpy_op = mapped

        steps: list[PlanStep] = []
        if wants_fetch or wants_analyst:
            steps.append(
                PlanStep(
                    step_id="fetch-1",
                    agent="data_fetcher",
                    instruction="Retrieve tabular rows via MCP Postgres interface.",
                    sql=None,
                    data_key="rows",
                )
            )
        if wants_analyst:
            steps.append(
                PlanStep(
                    step_id="analyze-1",
                    agent="analyst",
                    instruction="Run NumPy reduction on fetched rows.",
                    data_key="stats",
                    input_data_key="rows",
                    numpy_op=numpy_op,
                )
            )

        if not steps:
            steps = [
                PlanStep(
                    step_id="fetch-default",
                    agent="data_fetcher",
                    instruction="Default fetch for unspecified goal.",
                    sql=None,
                    data_key="rows",
                ),
                PlanStep(
                    step_id="analyze-default",
                    agent="analyst",
                    instruction="Default analysis for unspecified goal.",
                    data_key="stats",
                    input_data_key="rows",
                    numpy_op="mean",
                ),
            ]
        return steps

    def verify_step(self, step: PlanStep, artifacts: dict[str, Any]) -> VerificationResult:
        if step.data_key not in artifacts:
            return VerificationResult(
                ok=False,
                notes=[f"Missing artifact for data_key={step.data_key!r}"],
            )
        payload = artifacts[step.data_key]
        if step.agent == "data_fetcher" and not isinstance(payload, list):
            return VerificationResult(ok=False, notes=["Fetcher artifact must be a list of rows."])
        if step.agent == "analyst" and not isinstance(payload, dict):
            return VerificationResult(ok=False, notes=["Analyst artifact must be a dict summary."])
        return VerificationResult(ok=True, notes=[f"Step {step.step_id} verified."])

    def verify_run(
        self,
        goal: str,
        plan: list[PlanStep],
        artifacts: dict[str, Any],
    ) -> VerificationResult:
        _ = goal
        missing = [p.step_id for p in plan if p.data_key not in artifacts]
        if missing:
            return VerificationResult(
                ok=False,
                notes=[f"Final verification failed; missing steps: {missing}"],
            )
        return VerificationResult(ok=True, notes=["Final verification passed."])
