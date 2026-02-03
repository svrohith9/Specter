from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .models import ExecutionGraph, Node
from .streaming import StreamCallback
from ..healing.engine import HealingEngine
from ..skills.manager import SkillManager


class StreamingExecutor:
    def __init__(self, skills: SkillManager, healer: HealingEngine) -> None:
        self.skills = skills
        self.healer = healer

    async def execute(self, graph: ExecutionGraph, callback: StreamCallback) -> Any:
        sorted_nodes = graph.topological_sort()
        states = {n.id: "pending" for n in graph.nodes}
        results: Dict[str, Any] = {}
        progress = {"total": len(sorted_nodes), "completed": 0}

        semaphore = asyncio.Semaphore(graph.max_parallel)

        async def run_node(node: Node) -> None:
            async with semaphore:
                states[node.id] = "running"
                await callback.on_node_start(node, progress)
                try:
                    result = await asyncio.wait_for(
                        self._execute_node(node, results), timeout=node.timeout_seconds
                    )
                    states[node.id] = "completed"
                    results[node.id] = result
                    progress["completed"] += 1
                    if node.stream_output:
                        await callback.on_node_output(node, result, progress)
                except Exception as exc:  # noqa: BLE001
                    states[node.id] = "failed"
                    results[node.id] = exc
                    if node.error_strategy == "heal":
                        fix = await self.healer.attempt_fix(node, exc)
                        if fix.get("success"):
                            healed = await self._execute_node(node, results, fix.get("new_params"))
                            states[node.id] = "completed"
                            results[node.id] = healed
                            progress["completed"] += 1
                        else:
                            await callback.on_healing_failed(node, fix, progress)
                    else:
                        await callback.on_node_error(node, exc, progress)

        while not all(state == "completed" for state in states.values()):
            ready: List[Node] = []
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
        self, node: Node, results: Dict[str, Any], override_params: Dict[str, Any] | None = None
    ) -> Any:
        if node.type == "tool":
            params = override_params or node.spec.params
            return await self.skills.execute(node.spec.tool_name or "", params)
        if node.type == "llm":
            prompt = node.spec.prompt or ""
            return {"text": prompt}
        if node.type == "human_confirm":
            return {"approved": False}
        if node.type == "condition":
            return {"value": False}
        raise ValueError(f"Unknown node type: {node.type}")
