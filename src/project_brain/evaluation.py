"""Extension contracts for knowledge evaluation."""

from __future__ import annotations

from typing import Any, Protocol


class ModelAssistedEvaluator(Protocol):
    """Optional advisory adapter; implementations never receive promotion authority."""

    def evaluate(
        self,
        proposal: dict[str, Any],
        deterministic_findings: dict[str, Any],
    ) -> dict[str, Any]:
        """Return labeled judgments, reasoning summaries, and cited artifact references."""
