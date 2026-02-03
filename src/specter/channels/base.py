from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Channel(ABC):
    @abstractmethod
    async def receive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def send(self, message: Dict[str, Any], context: Dict[str, Any]) -> None:
        raise NotImplementedError
