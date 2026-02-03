from __future__ import annotations

from typing import Any, Dict, List


class LLMRouter:
    def __init__(self, routes: List[Dict[str, Any]]) -> None:
        self.routes = routes

    async def generate(self, prompt: str) -> str:
        # Stub: integrate LiteLLM
        return prompt
