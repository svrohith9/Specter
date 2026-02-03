from __future__ import annotations

import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import aiosqlite

from ..config import settings
from ..core.reliability import CircuitBreaker, RetryPolicy
from .builtin.calc import calculate
from .builtin.calendar import calendar_create_event, calendar_list_events
from .builtin.email import email_search, email_send
from .builtin.file_ops import file_list, file_read, file_write
from .builtin.search import web_search
from .builtin.web import web_fetch


@dataclass
class ToolSpec:
    name: str
    description: str
    params: dict[str, str]
    category: str = "core"
    example: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "params": self.params,
            "category": self.category,
            "example": self.example,
        }


class SkillManager:
    def __init__(self) -> None:
        self._skills: dict[str, Any] = {}
        self._specs: dict[str, ToolSpec] = {}
        self._breakers: dict[str, CircuitBreaker] = {}
        self._audit_hook: callable | None = None
        self._retry = RetryPolicy(
            max_attempts=settings.specter.execution.retry_attempts,
            base_delay=settings.specter.execution.retry_base_delay,
            max_delay=settings.specter.execution.retry_max_delay,
        )
        self._register_builtin()

    def _register_builtin(self) -> None:
        self.register_tool(
            "calculate",
            calculate,
            ToolSpec(
                name="calculate",
                description="Evaluate a math expression safely.",
                params={"expression": "string"},
                category="core",
                example="calculate: 5 * (12 + 9)",
            ),
        )
        self.register_tool(
            "web_fetch",
            web_fetch,
            ToolSpec(
                name="web_fetch",
                description="Fetch text from a URL.",
                params={"url": "string", "timeout": "int", "max_chars": "int"},
                category="core",
                example="web_fetch: https://example.com",
            ),
        )
        self.register_tool(
            "web_search",
            web_search,
            ToolSpec(
                name="web_search",
                description="Search the web for a query.",
                params={"query": "string", "max_results": "int"},
                category="connectors",
                example="web_search: Specter execution graphs",
            ),
        )
        self.register_tool(
            "file_read",
            file_read,
            ToolSpec(
                name="file_read",
                description="Read a file within the workspace.",
                params={"path": "string", "max_chars": "int"},
                category="filesystem",
                example="file_read: README.md",
            ),
        )
        self.register_tool(
            "file_write",
            file_write,
            ToolSpec(
                name="file_write",
                description="Write a file within the workspace.",
                params={"path": "string", "content": "string", "append": "bool"},
                category="filesystem",
                example="file_write: notes/today.txt",
            ),
        )
        self.register_tool(
            "file_list",
            file_list,
            ToolSpec(
                name="file_list",
                description="List files in a workspace directory.",
                params={"path": "string", "pattern": "string"},
                category="filesystem",
                example="file_list: .",
            ),
        )
        self.register_tool(
            "calendar_list_events",
            calendar_list_events,
            ToolSpec(
                name="calendar_list_events",
                description="List calendar events (connector required).",
                params={"start": "string", "end": "string"},
                category="connectors",
                example="calendar_list_events: 2025-01-01 to 2025-01-07",
            ),
        )
        self.register_tool(
            "calendar_create_event",
            calendar_create_event,
            ToolSpec(
                name="calendar_create_event",
                description="Create a calendar event (connector required).",
                params={"title": "string", "start": "string", "end": "string"},
                category="connectors",
                example="calendar_create_event: Demo, 2025-01-02 10:00",
            ),
        )
        self.register_tool(
            "email_send",
            email_send,
            ToolSpec(
                name="email_send",
                description="Send an email (connector required).",
                params={"to": "string", "subject": "string", "body": "string"},
                category="connectors",
                example="email_send: ops@example.com",
            ),
        )
        self.register_tool(
            "email_search",
            email_search,
            ToolSpec(
                name="email_search",
                description="Search mailbox (connector required).",
                params={"query": "string", "max_results": "int"},
                category="connectors",
                example="email_search: subject:invoice",
            ),
        )

    def register(self, name: str, func: Any) -> None:
        self._skills[name] = func
        self._breakers.setdefault(
            name,
            CircuitBreaker(
                threshold=settings.specter.execution.circuit_breaker_threshold,
                recovery_seconds=settings.specter.execution.circuit_breaker_timeout,
            ),
        )

    def register_tool(self, name: str, func: Any, spec: ToolSpec) -> None:
        self.register(name, func)
        self._specs[name] = spec

    def list(self) -> list[str]:
        return sorted(self._skills.keys())

    def list_specs(self) -> list[dict[str, Any]]:
        return [self._specs[name].to_dict() for name in sorted(self._specs.keys())]

    def describe(self, name: str) -> dict[str, Any] | None:
        spec = self._specs.get(name)
        return spec.to_dict() if spec else None

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
                    json.dumps(payload.get("signature", {})),
                    payload.get("code", json.dumps(payload)),
                    next_version,
                ),
            )
            await db.commit()

    async def _register_from_code(self, name: str, code: str) -> None:
        try:
            payload = json.loads(code)
        except Exception:
            payload = None

        if isinstance(payload, dict) and "description" in payload:
            async def skill(**params: Any) -> dict[str, Any]:
                return {
                    "success": True,
                    "data": {"payload": payload, "params": params},
                    "error": None,
                }

            self.register(name, skill)
            return

        allowed_modules = {"json", "re", "math", "datetime", "httpx"}

        def safe_import(module_name: str, *args: Any, **kwargs: Any) -> Any:
            if module_name in allowed_modules:
                return __import__(module_name, *args, **kwargs)
            raise ImportError(f"Module not allowed: {module_name}")

        safe_builtins = {
            "dict": dict,
            "list": list,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "len": len,
            "range": range,
            "min": min,
            "max": max,
            "sum": sum,
            "print": print,
            "Exception": Exception,
            "__import__": safe_import,
        }

        scope: dict[str, Any] = {"__builtins__": MappingProxyType(safe_builtins)}
        try:
            exec(code, scope)
            run_fn = scope.get("run")
            if run_fn is None:
                return
        except Exception:
            return

        async def skill(**params: Any) -> dict[str, Any]:
            return await run_fn(params)

        self.register(name, skill)

    async def execute(self, name: str, params: dict[str, Any]) -> Any:
        if name not in self._skills:
            raise ValueError(f"Unknown skill: {name}")
        breaker = self._breakers[name]
        if not breaker.allow():
            raise RuntimeError(f"Circuit open for tool: {name}")

        async def _call() -> Any:
            if self._audit_hook:
                await self._audit_hook("tool_call", {"tool": name, "params": params})
            fn = self._skills[name]
            return await fn(**params)

        try:
            result = await self._retry.run(_call)
            breaker.record_success()
            return result
        except Exception:
            breaker.record_failure()
            raise
