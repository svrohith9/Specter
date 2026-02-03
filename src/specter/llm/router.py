from __future__ import annotations

import os
from typing import Any

from litellm import acompletion

from ..config import settings
from ..core.reliability import RetryPolicy


class LLMError(RuntimeError):
    pass


class LLMRouter:
    def __init__(self, routes: list[dict[str, Any]] | None = None) -> None:
        raw_routes = routes or settings.specter.llm.get("router", [])
        self.routes: list[dict[str, Any]] = []
        self._retry = RetryPolicy(
            max_attempts=settings.specter.execution.retry_attempts,
            base_delay=settings.specter.execution.retry_base_delay,
            max_delay=settings.specter.execution.retry_max_delay,
        )
        for route in raw_routes:
            if isinstance(route, dict):
                if self._route_enabled(route):
                    self.routes.append(route)
            else:
                model_dump = route.model_dump()
                if self._route_enabled(model_dump):
                    self.routes.append(model_dump)

    @staticmethod
    def _route_enabled(route: dict[str, Any]) -> bool:
        if route.get("local"):
            return True
        provider = (route.get("provider") or "").lower()
        env_requirements = {
            "openai": ["OPENAI_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY"],
            "perplexity": ["PERPLEXITY_API_KEY"],
            "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        }
        keys = env_requirements.get(provider)
        if not keys:
            return True
        return any(os.getenv(key) for key in keys)

    async def generate(
        self,
        prompt: str,
        json_schema: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self.routes:
            return prompt
        errors: list[str] = []
        for route in sorted(self.routes, key=lambda r: r.get("priority", 1)):
            try:
                provider = route.get("provider")
                model = route["model"]
                if provider and "/" not in model:
                    model = f"{provider}/{model}"
                params: dict[str, Any] = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "timeout": route.get("timeout", 15),
                }
                if temperature is not None:
                    params["temperature"] = temperature
                if json_schema:
                    params["response_format"] = {
                        "type": "json_schema",
                        "json_schema": json_schema,
                    }
                async def _call(call_params: dict[str, Any] = params) -> Any:
                    return await acompletion(**call_params)

                resp = await self._retry.run(_call)
                content = resp.choices[0].message.content
                if not content:
                    raise LLMError("Empty response")
                return content
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{route.get('provider')}:{route.get('model')}: {exc}")
                continue
        raise LLMError("All LLM routes failed: " + "; ".join(errors))
