from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from agents.analyst import run_analyst_step
from agents.base_manager import BaseManager
from agents.data_fetcher import run_data_fetcher_step_async
from schema.plan import WorkflowStatus
from schema.state import WorkflowGraphState
from schema.workflow_protocol import InvokableWorkflowGraph
from tools.data_fetch_client import AsyncDataFetchClient


@dataclass(frozen=True, slots=True)
class WorkflowDependencies:
    data_fetch: AsyncDataFetchClient
    manager: BaseManager


def _route_after_verify(state: WorkflowGraphState) -> Literal["continue", "stop"]:
    status: WorkflowStatus | None = state.get("status")  # type: ignore[assignment]
    if status in ("failed", "done"):
        return "stop"
    return "continue"


def _route_after_plan(state: WorkflowGraphState) -> Literal["continue", "stop"]:
    status: WorkflowStatus | None = state.get("status")  # type: ignore[assignment]
    if status == "failed":
        return "stop"
    return "continue"


def build_workflow_graph(deps: WorkflowDependencies) -> InvokableWorkflowGraph:
    """Compile the Plan → Execute → Verify loop as a LangGraph state machine (async)."""

    async def manager_plan(state: WorkflowGraphState) -> dict[str, Any]:
        goal = state.get("goal", "")
        plan_existing = state.get("plan")
        if plan_existing is None:
            planned = deps.manager.plan(goal, {})
        else:
            planned = plan_existing
        if not planned:
            return {
                "status": "failed",
                "error": "No plan steps available.",
                "verification_notes": ["Planning produced an empty plan."],
            }
        return {
            "plan": planned,
            "current_step_index": 0,
            "status": "executing",
        }

    async def execute_current(state: WorkflowGraphState) -> dict[str, Any]:
        plan = state.get("plan") or []
        idx = int(state.get("current_step_index", 0))
        if idx >= len(plan):
            return {
                "status": "failed",
                "error": "execute_current called with no remaining steps.",
                "verification_notes": ["Executor index out of range."],
            }
        step = plan[idx]
        try:
            if step.agent == "data_fetcher":
                rows = await run_data_fetcher_step_async(step, deps.data_fetch)
                return {"artifacts": {step.data_key: rows}, "status": "verifying"}
            if step.agent == "analyst":
                artifacts = dict(state.get("artifacts") or {})
                summary = run_analyst_step(step, artifacts)
                return {"artifacts": {step.data_key: summary}, "status": "verifying"}
        except Exception as exc:  # noqa: BLE001 — surface any tool/agent failure to the graph state
            return {
                "status": "failed",
                "error": str(exc),
                "verification_notes": [f"Execution error on step {step.step_id}: {exc}"],
            }
        return {
            "status": "failed",
            "error": f"Unknown agent {step.agent!r}",
            "verification_notes": ["Unknown agent in plan step."],
        }

    async def manager_verify(state: WorkflowGraphState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}
        plan = state.get("plan") or []
        idx = int(state.get("current_step_index", 0))
        if idx >= len(plan):
            return {}
        step = plan[idx]
        artifacts = dict(state.get("artifacts") or {})
        step_result = deps.manager.verify_step(step, artifacts)
        notes = list(step_result.notes)
        if not step_result.ok:
            return {
                "status": "failed",
                "error": "; ".join(notes) if notes else "Step verification failed.",
                "verification_notes": notes,
            }
        next_idx = idx + 1
        if next_idx >= len(plan):
            final = deps.manager.verify_run(state.get("goal", ""), plan, artifacts)
            merged_notes = notes + list(final.notes)
            if not final.ok:
                return {
                    "current_step_index": next_idx,
                    "status": "failed",
                    "error": "; ".join(final.notes),
                    "verification_notes": merged_notes,
                }
            return {
                "current_step_index": next_idx,
                "status": "done",
                "verification_notes": merged_notes,
            }
        return {
            "current_step_index": next_idx,
            "status": "executing",
            "verification_notes": notes,
        }

    graph = StateGraph(WorkflowGraphState)
    graph.add_node("manager_plan", manager_plan)
    graph.add_node("execute_current", execute_current)
    graph.add_node("manager_verify", manager_verify)

    graph.add_edge(START, "manager_plan")
    graph.add_conditional_edges(
        "manager_plan",
        _route_after_plan,
        {"continue": "execute_current", "stop": END},
    )
    graph.add_edge("execute_current", "manager_verify")
    graph.add_conditional_edges(
        "manager_verify",
        _route_after_verify,
        {"continue": "execute_current", "stop": END},
    )

    return graph.compile()
