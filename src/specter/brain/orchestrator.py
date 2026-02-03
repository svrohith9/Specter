from __future__ import annotations

from typing import Any

from ..graph.compiler import IntentCompiler
from ..graph.executor import StreamingExecutor
from ..graph.streaming import StreamCallback
from ..healing.engine import HealingEngine
from ..skills.manager import SkillManager


class Orchestrator:
    def __init__(self) -> None:
        self.skills = SkillManager()
        self.healer = HealingEngine()
        self.compiler = IntentCompiler()
        self.executor = StreamingExecutor(self.skills, self.healer)

    async def run(self, user_input: str, context: dict[str, Any], callback: StreamCallback) -> Any:
        graph = await self.compiler.compile(user_input, context)
        return await self.executor.execute(graph, callback)
