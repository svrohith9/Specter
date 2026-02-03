from __future__ import annotations

import json
from typing import Any

import aiosqlite

from .builtin.calc import calculate
from .builtin.web import web_fetch


class SkillManager:
    def __init__(self) -> None:
        self._skills: dict[str, Any] = {}
        self.register("calculate", calculate)
        self.register("web_fetch", web_fetch)
        self._audit_hook: callable | None = None

    def register(self, name: str, func: Any) -> None:
        self._skills[name] = func

    def list(self) -> list[str]:
        return sorted(self._skills.keys())

    def set_audit_hook(self, hook: callable | None) -> None:
        self._audit_hook = hook

    async def load_from_db(self, db_path: str) -> None:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("SELECT name, code FROM skills")
            rows = await cursor.fetchall()
            for name, code in rows:
                await self._register_from_code(name, code)

    async def persist_template_skill(
        self, db_path: str, name: str, payload: dict[str, Any]
    ) -> None:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "SELECT MAX(version) FROM skills WHERE name = ?",
                (name,),
            )
            row = await cursor.fetchone()
            next_version = (row[0] or 0) + 1
            await db.execute(
                """
                INSERT OR REPLACE INTO skills (id, name, description, signature, code, version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{name}_v{next_version}",
                    name,
                    payload.get("description"),
                    "{}",
                    json.dumps(payload),
                    next_version,
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
        if self._audit_hook:
            await self._audit_hook("tool_call", {"tool": name, "params": params})
        fn = self._skills[name]
        return await fn(**params)
