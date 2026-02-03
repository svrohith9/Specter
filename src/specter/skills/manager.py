from __future__ import annotations

from typing import Any

import aiosqlite
import json

from .builtin.calc import calculate
from .builtin.web import web_fetch


class SkillManager:
    def __init__(self) -> None:
        self._skills: dict[str, Any] = {}
        self.register("calculate", calculate)
        self.register("web_fetch", web_fetch)

    def register(self, name: str, func: Any) -> None:
        self._skills[name] = func

    async def load_from_db(self, db_path: str) -> None:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("SELECT name, code FROM skills")
            rows = await cursor.fetchall()
            for name, code in rows:
                await self._register_from_code(name, code)

    async def persist_template_skill(self, db_path: str, name: str, payload: dict[str, Any]) -> None:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO skills (id, name, description, signature, code, version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{name}_v1",
                    name,
                    payload.get("description"),
                    "{}",
                    json.dumps(payload),
                    1,
                ),
            )
            await db.commit()

    async def _register_from_code(self, name: str, code: str) -> None:
        # Minimal safe loader for template skills (JSON dict)
        try:
            payload = json.loads(code)
        except Exception:
            return

        async def skill(**params: Any) -> dict[str, Any]:
            return {
                "success": True,
                "data": {"payload": payload, "params": params},
                "error": None,
            }

        self.register(name, skill)
    async def execute(self, name: str, params: dict[str, Any]) -> Any:
        if name not in self._skills:
            raise ValueError(f"Unknown skill: {name}")
        fn = self._skills[name]
        return await fn(**params)
