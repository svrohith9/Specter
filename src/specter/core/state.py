from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UserState:
    user_id: str
    focus_mode: str = "available"
    current_activity: str = "idle"
    recent_actions: list[dict[str, Any]] = field(default_factory=list)
    timezone: str = "UTC"
    sleeping: bool = False
    wake_time: str | None = None
