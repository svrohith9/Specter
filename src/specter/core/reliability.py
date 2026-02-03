from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.4
    max_delay: float = 4.0
    jitter: float = 0.2

    async def run(
        self,
        func: Callable[[], Awaitable[Any]],
        on_retry: Callable[[int, Exception], Awaitable[None]] | None = None,
    ) -> Any:
        attempt = 1
        while True:
            try:
                return await func()
            except Exception as exc:  # noqa: BLE001
                if attempt >= self.max_attempts:
                    raise
                if on_retry:
                    await on_retry(attempt, exc)
                delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
                delay = delay + random.uniform(0, self.jitter)
                await asyncio.sleep(delay)
                attempt += 1


class CircuitBreaker:
    def __init__(self, threshold: int = 3, recovery_seconds: int = 30) -> None:
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at >= self.recovery_seconds:
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.time()
