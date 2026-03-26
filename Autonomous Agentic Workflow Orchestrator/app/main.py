from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast

from fastapi import FastAPI, HTTPException
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from app.graph import WorkflowDependencies, build_workflow_graph
from app.settings import OrchestratorSettings
from agents.manager_agent import HeuristicManager
from schema.api import HealthResponse, RunWorkflowRequest, RunWorkflowResponse
from schema.plan import WorkflowStatus
from schema.state import WorkflowGraphState
from schema.workflow_protocol import InvokableWorkflowGraph
from tools.data_fetch_client import StubAsyncDataFetchClient
from tools.sqlite_mcp_client import McpSqliteDataFetchClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = OrchestratorSettings()
    if settings.sqlite_db_path is not None:
        db_path = settings.sqlite_db_path.resolve()
        if not db_path.is_file():
            msg = f"SQLITE_DB_PATH does not exist or is not a file: {db_path}"
            raise RuntimeError(msg)
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.sqlite_server"],
            env={**os.environ, "SQLITE_MCP_DB_PATH": str(db_path)},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                client: McpSqliteDataFetchClient | StubAsyncDataFetchClient = McpSqliteDataFetchClient(
                    session
                )
                deps = WorkflowDependencies(data_fetch=client, manager=HeuristicManager())
                app.state.graph = build_workflow_graph(deps)
                yield
    else:
        app.state.graph = build_workflow_graph(
            WorkflowDependencies(data_fetch=StubAsyncDataFetchClient(), manager=HeuristicManager())
        )
        yield


app = FastAPI(
    title="Agentic Workflow Orchestrator",
    version="0.2.0",
    description="Manager agent with Data-Fetcher (MCP SQLite + NL→SQL) and Analyst (NumPy) sub-agents.",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/workflow/run", response_model=RunWorkflowResponse)
async def run_workflow(body: RunWorkflowRequest) -> RunWorkflowResponse:
    initial: dict[str, Any] = {
        "goal": body.goal,
        "current_step_index": 0,
        "artifacts": {},
        "verification_notes": [],
        "status": "planning",
    }
    if body.plan_override is not None:
        initial["plan"] = body.plan_override

    graph = cast(InvokableWorkflowGraph, app.state.graph)
    try:
        final = cast(WorkflowGraphState, await graph.ainvoke(initial))
    except Exception as exc:  # pragma: no cover - defensive for unexpected graph errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    plan_out = list(final.get("plan") or [])
    artifacts_out: dict[str, Any] = dict(final.get("artifacts") or {})
    notes_out = list(final.get("verification_notes") or [])
    status: WorkflowStatus = cast(WorkflowStatus, final.get("status", "failed"))
    err = final.get("error")

    return RunWorkflowResponse(
        status=status,
        plan=plan_out,
        artifacts=artifacts_out,
        verification_notes=notes_out,
        error=err,
    )
