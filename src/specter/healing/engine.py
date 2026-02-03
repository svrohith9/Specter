from __future__ import annotations

from typing import Any

from ..graph.models import Node


class HealingEngine:
    FAILURE_PATTERNS = {
        "SyntaxError": "syntax_repair",
        "APIStatusError": "api_diagnosis",
        "RateLimitError": "backoff_retry",
        "AuthenticationError": "credential_refresh",
    }

    async def attempt_fix(self, node: Node, error: Exception) -> dict[str, Any]:
        error_type = type(error).__name__
        strategy = self.FAILURE_PATTERNS.get(error_type, "escalate")
        return {
            "success": False,
            "strategy": strategy,
            "error": str(error),
        }
