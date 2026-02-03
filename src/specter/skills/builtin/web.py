from __future__ import annotations

import re
from typing import Any

import httpx


async def web_fetch(url: str, timeout: int = 10, max_chars: int = 5000) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            text = resp.text
            if "<html" in text.lower():
                text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return {"success": True, "data": text[:max_chars], "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "data": None, "error": str(exc)}
