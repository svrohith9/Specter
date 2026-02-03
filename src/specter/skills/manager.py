from __future__ import annotations

from typing import Any, Dict


class SkillManager:
    def __init__(self) -> None:
        self._skills: Dict[str, Any] = {}

    def register(self, name: str, func: Any) -> None:
        self._skills[name] = func

    async def execute(self, name: str, params: Dict[str, Any]) -> Any:
        if name not in self._skills:
            raise ValueError(f"Unknown skill: {name}")
        fn = self._skills[name]
        return await fn(**params)
