from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from .models import ExecutionGraph, ExecutionPlan, Node


class IntentCompiler:
    SYSTEM_PROMPT = (
        "You are an execution planner. Convert user requests into JSON DAGs."
    )

    async def compile(self, user_input: str, context: Dict[str, Any]) -> ExecutionGraph:
        # Placeholder: deterministic single-node graph
        node = Node(
            id="llm_1",
            type="llm",
            spec={"prompt": f"Respond to: {user_input}"},
            deps=[],
            error_strategy="heal",
        )
        plan = ExecutionPlan(
            intent_summary=user_input,
            confidence=0.3,
            nodes=[node],
        )
        return ExecutionGraph(nodes=plan.nodes, max_parallel=1)

    def _context_payload(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "time": datetime.utcnow().isoformat(),
            **context,
        }
