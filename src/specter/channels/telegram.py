from __future__ import annotations

from typing import Any, Dict

from .base import Channel


class TelegramChannel(Channel):
    async def receive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        message = payload.get("message", {})
        return {
            "user_id": str(message.get("from", {}).get("id", "")),
            "text": message.get("text", ""),
        }

    async def send(self, message: Dict[str, Any], context: Dict[str, Any]) -> None:
        # Stub: integrate Telegram Bot API
        return None
