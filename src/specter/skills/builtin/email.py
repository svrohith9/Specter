from __future__ import annotations


async def email_send(to: str, subject: str, body: str) -> dict:
    return {
        "success": False,
        "data": None,
        "error": "Email connector not configured. Set SMTP credentials to enable.",
    }


async def email_search(query: str, max_results: int = 5) -> dict:
    return {
        "success": False,
        "data": None,
        "error": "Email connector not configured. Set IMAP credentials to enable.",
    }
