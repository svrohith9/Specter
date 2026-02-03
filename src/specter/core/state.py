from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UserState:
    user_id: str
    focus_mode: str = "available"
    current_activity: str = "idle"
    recent_actions: List[Dict[str, Any]] = field(default_factory=list)
    timezone: str = "UTC"
    sleeping: bool = False
    wake_time: Optional[str] = None
