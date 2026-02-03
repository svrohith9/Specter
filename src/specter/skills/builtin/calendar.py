from __future__ import annotations


async def calendar_list_events(start: str, end: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": "Calendar connector not configured. Provide OAuth credentials to enable.",
    }


async def calendar_create_event(title: str, start: str, end: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": "Calendar connector not configured. Provide OAuth credentials to enable.",
    }
