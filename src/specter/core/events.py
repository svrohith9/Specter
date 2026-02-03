from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], Any]]] = {}

    def subscribe(self, event: str, handler: Callable[[Any], Any]) -> None:
        self._subscribers.setdefault(event, []).append(handler)

    async def publish(self, event: str, payload: Any) -> None:
        handlers = self._subscribers.get(event, [])
        if not handlers:
            return
        await asyncio.gather(*(handler(payload) for handler in handlers))
