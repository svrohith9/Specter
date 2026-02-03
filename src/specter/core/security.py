from __future__ import annotations

from dataclasses import dataclass

from ..config import SecurityConfig


@dataclass
class ToolPolicy:
    allowed: set[str]
    blocked: set[str]

    def check(self, tool_name: str) -> None:
        if tool_name in self.blocked:
            raise PermissionError(f"Tool blocked: {tool_name}")
        if self.allowed and tool_name not in self.allowed:
            raise PermissionError(f"Tool not in allowlist: {tool_name}")


def load_tool_policy(security: SecurityConfig) -> ToolPolicy:
    return ToolPolicy(allowed=set(security.allowed_tools), blocked=set(security.blocked_tools))
