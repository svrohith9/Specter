from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .models import ExecutionGraph, ExecutionPlan, Node
from ..llm.router import LLMRouter


class PlanSchema(BaseModel):
    intent_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    nodes: List[Node]


class IntentCompiler:
    SYSTEM_PROMPT = (
        "You are an execution planner. Convert user requests into JSON DAGs."
    )

    async def compile(self, user_input: str, context: Dict[str, Any]) -> ExecutionGraph:
        router = LLMRouter()
        schema = PlanSchema.model_json_schema()
        prompt = self._build_prompt(user_input, context)
        try:
            raw = await router.generate(prompt, json_schema=schema)
            data = json.loads(raw)
            plan = PlanSchema(**data)
            return ExecutionGraph(nodes=plan.nodes, max_parallel=10)
        except Exception:
            # Safe fallback: deterministic single-node graph
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

    def _build_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        payload = self._context_payload(context)
        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            "Rules:\n"
            "1. Maximize parallelization (independent nodes parallel).\n"
            "2. Minimize LLM calls when tools suffice.\n"
            "3. Ensure DAG has no cycles.\n\n"
            f"User request: {user_input}\n"
            f"Context: {json.dumps(payload)}\n"
            "Return only JSON that matches the schema."
        )
