from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..config import settings
from ..llm.router import LLMRouter
from .models import ExecutionGraph, ExecutionPlan, Node


class PlanSchema(BaseModel):
    intent_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    nodes: list[Node]


TOOL_CATALOG: list[dict[str, Any]] = [
    {
        "name": "calculate",
        "description": "Evaluate a math expression safely.",
        "params": {"expression": "string"},
    },
    {
        "name": "web_fetch",
        "description": "Fetch text from a URL.",
        "params": {"url": "string", "timeout": "int", "max_chars": "int"},
    },
    {
        "name": "web_search",
        "description": "Search the web for a query.",
        "params": {"query": "string", "max_results": "int"},
    },
    {
        "name": "file_read",
        "description": "Read a file from the workspace.",
        "params": {"path": "string", "max_chars": "int"},
    },
    {
        "name": "file_write",
        "description": "Write a file to the workspace.",
        "params": {"path": "string", "content": "string", "append": "bool"},
    },
    {
        "name": "file_list",
        "description": "List files in a workspace directory.",
        "params": {"path": "string", "pattern": "string"},
    },
    {
        "name": "calendar_list_events",
        "description": "List calendar events (connector required).",
        "params": {"start": "string", "end": "string"},
    },
    {
        "name": "calendar_create_event",
        "description": "Create a calendar event (connector required).",
        "params": {"title": "string", "start": "string", "end": "string"},
    },
    {
        "name": "email_send",
        "description": "Send an email (connector required).",
        "params": {"to": "string", "subject": "string", "body": "string"},
    },
    {
        "name": "email_search",
        "description": "Search email (connector required).",
        "params": {"query": "string", "max_results": "int"},
    },
]


class IntentCompiler:
    SYSTEM_PROMPT = (
        "You are an execution planner. Convert user requests into JSON DAGs."
    )

    async def compile(self, user_input: str, context: dict[str, Any]) -> ExecutionGraph:
        router = LLMRouter()
        schema = PlanSchema.model_json_schema()
        prompt = self._build_prompt(user_input, context)
        try:
            temperature = 0.1 if settings.specter.execution.deterministic_planning else 0.3
            raw = await router.generate(prompt, json_schema=schema, temperature=temperature)
            data = json.loads(raw)
            plan = PlanSchema(**data)
            plan = self._normalize_plan(plan)
            self._validate_plan(plan)
            return ExecutionGraph(nodes=plan.nodes, max_parallel=10)
        except Exception:
            return self._fallback_graph(user_input)

    def _context_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "time": datetime.utcnow().isoformat(),
            **context,
        }

    def _build_prompt(self, user_input: str, context: dict[str, Any]) -> str:
        payload = self._context_payload(context)
        return (
            f"{self.SYSTEM_PROMPT}\n\n"
            "Rules:\n"
            "1. Maximize parallelization (independent nodes parallel).\n"
            "2. Minimize LLM calls when tools suffice.\n"
            "3. Ensure DAG has no cycles.\n\n"
            f"Available tools:\n{json.dumps(TOOL_CATALOG)}\n\n"
            f"User request: {user_input}\n"
            f"Context: {json.dumps(payload)}\n"
            "Return only JSON that matches the schema."
        )

    def _validate_plan(self, plan: PlanSchema) -> None:
        node_ids = [n.id for n in plan.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("Duplicate node ids")
        id_set = set(node_ids)
        for node in plan.nodes:
            if node.type not in {"tool", "llm", "condition", "human_confirm"}:
                raise ValueError(f"Invalid node type: {node.type}")
            for dep in node.deps:
                if dep not in id_set:
                    raise ValueError(f"Unknown dependency: {dep}")
            if node.type == "tool" and not node.spec.tool_name:
                raise ValueError("Tool node missing tool_name")
        self._assert_acyclic(plan.nodes)

    def _normalize_plan(self, plan: PlanSchema) -> PlanSchema:
        # Ensure deterministic node ids if missing or empty
        normalized: list[Node] = []
        for idx, node in enumerate(plan.nodes, start=1):
            if not node.id:
                node.id = f"node_{idx}"
            normalized.append(node)
        return PlanSchema(
            intent_summary=plan.intent_summary,
            confidence=plan.confidence,
            nodes=normalized,
        )

    def _assert_acyclic(self, nodes: list[Node]) -> None:
        deps = {n.id: set(n.deps) for n in nodes}
        visited: set[str] = set()
        stack: set[str] = set()

        def visit(nid: str) -> None:
            if nid in stack:
                raise ValueError("Cycle detected in graph")
            if nid in visited:
                return
            stack.add(nid)
            for dep in deps.get(nid, set()):
                visit(dep)
            stack.remove(nid)
            visited.add(nid)

        for nid in deps:
            visit(nid)

    def _fallback_graph(self, user_input: str) -> ExecutionGraph:
        text = user_input.strip()
        if re.search(r"https?://", text):
            node = Node(
                id="tool_1",
                type="tool",
                spec={"tool_name": "web_fetch", "params": {"url": text}},
                deps=[],
                error_strategy="heal",
            )
            return ExecutionGraph(nodes=[node], max_parallel=1)
        if re.fullmatch(r"[0-9+\-*/().\s]+", text):
            node = Node(
                id="tool_1",
                type="tool",
                spec={"tool_name": "calculate", "params": {"expression": text}},
                deps=[],
                error_strategy="heal",
            )
            return ExecutionGraph(nodes=[node], max_parallel=1)
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
