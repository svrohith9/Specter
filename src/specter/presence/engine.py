from __future__ import annotations

from dataclasses import dataclass

from ..graph.models import ExecutionGraph


@dataclass
class RiskAssessment:
    level: float
    requires_confirmation: bool


class PresenceEngine:
    def calculate_risk(self, graph: ExecutionGraph) -> RiskAssessment:
        return RiskAssessment(level=0.1, requires_confirmation=False)
