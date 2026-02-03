from __future__ import annotations

from typing import Any

from litellm import acompletion

from ..config import settings


class LLMError(RuntimeError):
    pass


class LLMRouter:
    def __init__(self, routes: list[dict[str, Any]] | None = None) -> None:
        self.routes = routes or settings.specter.llm.get("router", [])

    async def generate(self, prompt: str, json_schema: dict[str, Any] | None = None) -> str:
        if not self.routes:
            return prompt
        errors: list[str] = []
        for route in sorted(self.routes, key=lambda r: r.get("priority", 1)):
            try:
                model = route["model"]
                params: dict[str, Any] = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "timeout": route.get("timeout", 15),
                }
                if json_schema:
                    params["response_format"] = {
                        "type": "json_schema",
                        "json_schema": json_schema,
                    }
                resp = await acompletion(**params)
                content = resp.choices[0].message.content
                if not content:
                    raise LLMError("Empty response")
                return content
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{route.get('provider')}:{route.get('model')}: {exc}")
                continue
        raise LLMError("All LLM routes failed: " + "; ".join(errors))
