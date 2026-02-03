from __future__ import annotations

import re

import httpx


async def web_search(query: str, max_results: int = 5) -> dict:
    url = "https://duckduckgo.com/html/"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params={"q": query})
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "data": None, "error": f"Search failed: {exc}"}

    links = re.findall(r'href=\"(https?://[^\"]+)\"', resp.text)
    results = []
    for link in links:
        if "duckduckgo.com" in link:
            continue
        results.append(link)
        if len(results) >= max_results:
            break
    return {"success": True, "data": {"query": query, "results": results}, "error": None}
