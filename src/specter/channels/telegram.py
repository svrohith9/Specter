from __future__ import annotations

from typing import Any

from .base import Channel


class TelegramChannel(Channel):
    async def receive(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload.get("message", {})
        return {
            "user_id": str(message.get("from", {}).get("id", "")),
            "text": message.get("text", ""),
        }

    async def send(self, message: dict[str, Any], context: dict[str, Any]) -> None:
        # Stub: integrate Telegram Bot API
        return None
