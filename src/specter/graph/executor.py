from __future__ import annotations

import asyncio
from typing import Any

from ..core.security import ToolPolicy
from ..healing.engine import HealingEngine
from ..llm.router import LLMRouter
from ..skills.manager import SkillManager
from .models import ExecutionGraph, Node
from .streaming import StreamCallback


class StreamingExecutor:
    def __init__(self, skills: SkillManager, healer: HealingEngine, policy: ToolPolicy) -> None:
        self.skills = skills
        self.healer = healer
        self.llm = LLMRouter()
        self.policy = policy

    async def execute(
        self,
        graph: ExecutionGraph,
        callback: StreamCallback,
        audit: callable | None = None,
    ) -> Any:
        sorted_nodes = graph.topological_sort()
        states = {n.id: "pending" for n in graph.nodes}
        results: dict[str, Any] = {}
        progress = {"total": len(sorted_nodes), "completed": 0}

        semaphore = asyncio.Semaphore(graph.max_parallel)

        async def run_node(node: Node) -> None:
            async with semaphore:
                states[node.id] = "running"
                await callback.on_node_start(node, progress)
                try:
                    result = await asyncio.wait_for(
                        self._execute_node(node, results, audit), timeout=node.timeout_seconds
                    )
                    states[node.id] = "completed"
                    results[node.id] = result
                    progress["completed"] += 1
                    if node.stream_output:
                        await callback.on_node_output(node, result, progress)
                except Exception as exc:  # noqa: BLE001
                    states[node.id] = "failed"
                    results[node.id] = exc
                    if node.error_strategy == "retry":
                        try:
                            result = await asyncio.wait_for(
                                self._execute_node(node, results, audit), timeout=node.timeout_seconds
                            )
                            states[node.id] = "completed"
                            results[node.id] = result
                            progress["completed"] += 1
                            return
                        except Exception:
                            pass
                    if node.error_strategy == "heal":
                        fix = await self.healer.attempt_fix(node, exc)
                        if fix.get("success"):
                            healed = await self._execute_node(
                                node, results, audit, fix.get("new_params")
                            )
                            states[node.id] = "completed"
                            results[node.id] = healed
                            progress["completed"] += 1
                        else:
                            await callback.on_healing_failed(node, fix, progress)
                    else:
                        await callback.on_node_error(node, exc, progress)

        while not all(state == "completed" for state in states.values()):
            ready: list[Node] = []
            for n in sorted_nodes:
                if states[n.id] != "pending":
                    continue
                if all(dep in results for dep in n.deps):
                    ready.append(n)

            if not ready:
                await asyncio.sleep(0.01)
                continue

            await asyncio.gather(*(run_node(n) for n in ready))

        final = {"results": results, "progress": progress}
        await callback.on_complete(final)
        return final

    async def _execute_node(
        self,
        node: Node,
        results: dict[str, Any],
        audit: callable | None = None,
        override_params: dict[str, Any] | None = None,
    ) -> Any:
        if node.type == "tool":
            params = override_params or node.spec.params
            try:
                self.policy.check(node.spec.tool_name or "")
            except Exception as exc:  # noqa: BLE001
                if audit:
                    await audit("policy_block", {"tool": node.spec.tool_name, "error": str(exc)})
                raise
            return await self.skills.execute(node.spec.tool_name or "", params)
        if node.type == "llm":
            prompt = node.spec.prompt or ""
            text = await self.llm.generate(prompt)
            return {"text": text}
        if node.type == "human_confirm":
            return {"approved": False}
        if node.type == "condition":
            return {"value": False}
        raise ValueError(f"Unknown node type: {node.type}")
