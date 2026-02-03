from __future__ import annotations

from __future__ import annotations

import re
from typing import Any, Callable


class SkillForge:
    def __init__(self, register: Callable[[str, Any], None]) -> None:
        self._register = register

    async def forge(
        self, description: str, examples: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        name = self._slugify(description)

        async def skill(**params: Any) -> dict[str, Any]:
            return {
                "success": True,
                "data": {"description": description, "params": params, "examples": examples or []},
                "error": None,
            }

        self._register(name, skill)
        return {
            "created": True,
            "skill": {
                "id": f"{name}_v1",
                "name": name,
                "description": description,
                "version": 1,
            },
        }

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
        return slug.strip("_") or "skill"
