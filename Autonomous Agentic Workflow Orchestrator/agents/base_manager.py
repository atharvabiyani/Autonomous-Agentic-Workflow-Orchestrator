from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from schema.plan import PlanStep, VerificationResult


class BaseManager(ABC):
    """
    Plan → Execute → Verify loop for the Manager agent.

    Concrete implementations decide how plans are produced (LLM, rules, or hybrid)
    and what verification invariants must hold before advancing or finishing.
    """

    @abstractmethod
    def plan(self, goal: str, context: dict[str, Any]) -> list[PlanStep]:
        """Produce an ordered delegation plan for sub-agents."""

    @abstractmethod
    def verify_step(self, step: PlanStep, artifacts: dict[str, Any]) -> VerificationResult:
        """Validate the artifact produced for the current step."""

    @abstractmethod
    def verify_run(
        self,
        goal: str,
        plan: list[PlanStep],
        artifacts: dict[str, Any],
    ) -> VerificationResult:
        """Final cross-step verification before marking the workflow done."""
