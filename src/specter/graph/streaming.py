from __future__ import annotations

from typing import Any, Protocol

from .models import Node


class StreamCallback(Protocol):
    async def on_node_start(self, node: Node, progress: dict) -> None: ...

    async def on_node_output(self, node: Node, result: Any, progress: dict) -> None: ...

    async def on_node_error(self, node: Node, error: Exception, progress: dict) -> None: ...

    async def on_healing_failed(self, node: Node, fix: Any, progress: dict) -> None: ...

    async def on_complete(self, result: Any) -> None: ...
