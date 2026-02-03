from __future__ import annotations

from typing import Any

from ..core.security import ToolPolicy
from ..graph.compiler import IntentCompiler
from ..graph.executor import StreamingExecutor
from ..graph.streaming import StreamCallback
from ..healing.engine import HealingEngine
from ..skills.manager import SkillManager
from ..storage import ExecutionStore


class Orchestrator:
    def __init__(self, store: ExecutionStore, policy: ToolPolicy) -> None:
        self.skills = SkillManager()
        self.healer = HealingEngine()
        self.compiler = IntentCompiler()
        self.executor = StreamingExecutor(self.skills, self.healer, policy)
        self.store = store

    async def run(
        self, user_input: str, context: dict[str, Any], callback: StreamCallback
    ) -> dict[str, Any]:
        graph = await self.compiler.compile(user_input, context)
        exec_id = await self.store.create_execution(
            user_id=str(context.get("user_id", "local")),
            intent=user_input,
            graph=graph.model_dump(),
        )

        async def audit(action: str, details: dict[str, Any]) -> None:
            await self.store.add_audit(exec_id, action, details)

        self.skills.set_audit_hook(audit)

        try:
            result = await self.executor.execute(graph, callback, audit=audit)
            await self.store.complete_execution(exec_id, result)
            return {"execution_id": exec_id, "result": result}
        except Exception as exc:  # noqa: BLE001
            await self.store.fail_execution(exec_id, str(exc))
            raise
