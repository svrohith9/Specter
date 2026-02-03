from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Channel(ABC):
    @abstractmethod
    async def receive(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def send(self, message: dict[str, Any], context: dict[str, Any]) -> None:
        raise NotImplementedError
