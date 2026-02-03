from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from ..config import settings
from ..llm.router import LLMRouter


class KnowledgeGraph:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            for migration in sorted(Path("migrations").glob("*.sql")):
                with open(migration, encoding="utf-8") as f:
                    await db.executescript(f.read())
            await db.commit()
        await self.cleanup_expired()

    async def add_fact(self, statement: str, confidence: float = 1.0) -> str:
        fact_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        expires_at = self._expires_at("fact")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO entities (id, type, name, attributes, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (fact_id, "fact", statement[:128], json.dumps({"raw": statement}), now, expires_at),
            )
            entities = await self._extract_entities(statement)
            for ent in entities:
                ent_id = await self._get_or_create_entity(db, ent["type"], ent["name"], now)
                await db.execute(
                    """
                    INSERT INTO relationships (id, source_id, target_id, relation_type, strength, context, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        ent_id,
                        fact_id,
                        "mentioned_in",
                        confidence,
                        json.dumps({"statement": statement}),
                        now,
                    ),
                )
            await db.commit()
        return fact_id

    async def query(self, question: str, limit: int = 5) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, name, attributes FROM entities
                WHERE name LIKE ? OR attributes LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (f"%{question}%", f"%{question}%", limit),
            )
            rows = await cursor.fetchall()
            return [
                {"id": r[0], "name": r[1], "attributes": json.loads(r[2] or "{}")} for r in rows
            ]

    async def summarize_recent(self, limit: int | None = None) -> dict[str, Any]:
        window = limit or settings.specter.knowledge.summary_window
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT attributes FROM entities
                WHERE type = 'fact'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (window,),
            )
            rows = await cursor.fetchall()
        facts = [json.loads(r[0]).get("raw", "") for r in rows if r[0]]
        if not facts:
            return {"summary": "", "source_count": 0}
        summary = await self._summarize_texts(facts)
        summary_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO summaries (id, summary, source_count, created_at) VALUES (?, ?, ?, ?)",
                (summary_id, summary, len(facts), now),
            )
            await db.commit()
        return {"summary": summary, "source_count": len(facts), "id": summary_id}

    async def list_summaries(self, limit: int = 5) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, summary, source_count, created_at
                FROM summaries
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
        return [
            {"id": r[0], "summary": r[1], "source_count": r[2], "created_at": r[3]}
            for r in rows
        ]

    async def query_entities(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, type, name FROM entities
                WHERE name LIKE ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (f"%{query}%", limit),
            )
            rows = await cursor.fetchall()
            results: list[dict[str, Any]] = []
            for entity_id, ent_type, name in rows:
                rel_cursor = await db.execute(
                    """
                    SELECT relation_type, target_id FROM relationships
                    WHERE source_id = ? LIMIT 5
                    """,
                    (entity_id,),
                )
                rels = await rel_cursor.fetchall()
                results.append(
                    {
                        "id": entity_id,
                        "type": ent_type,
                        "name": name,
                        "relations": [{"type": r[0], "target_id": r[1]} for r in rels],
                    }
                )
            return results

    async def _extract_entities(self, text: str) -> list[dict[str, str]]:
        router = LLMRouter()
        if router.routes:
            prompt = (
                "Extract entities from the text. Return JSON array of objects with type and name.\n"
                "Types: person, org, location, concept, url, email, number.\n\n"
                f"Text: {text}\n"
            )
            try:
                raw = await router.generate(prompt)
                data = json.loads(raw)
                if isinstance(data, list):
                    return [
                        {"type": item.get("type", "concept"), "name": item.get("name", "")}
                        for item in data
                        if isinstance(item, dict) and item.get("name")
                    ]
            except Exception:
                pass

        entities: list[dict[str, str]] = []
        for email in re.findall(r"[\\w\\.-]+@[\\w\\.-]+", text):
            entities.append({"type": "email", "name": email})
        for url in re.findall(r"https?://\\S+", text):
            entities.append({"type": "url", "name": url})
        for number in re.findall(r"\\b\\d+(?:\\.\\d+)?\\b", text):
            entities.append({"type": "number", "name": number})
        for word in re.findall(r"\\b[A-Z][a-z]{2,}\\b", text):
            entities.append({"type": "proper_noun", "name": word})
        return entities

    async def _get_or_create_entity(
        self, db: aiosqlite.Connection, ent_type: str, name: str, now: str
    ) -> str:
        cursor = await db.execute(
            "SELECT id FROM entities WHERE type = ? AND name = ?",
            (ent_type, name),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        ent_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO entities (id, type, name, attributes, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ent_id, ent_type, name, json.dumps({}), now, self._expires_at(ent_type)),
        )
        return ent_id

    async def cleanup_expired(self) -> None:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                DELETE FROM relationships
                WHERE source_id IN (SELECT id FROM entities WHERE expires_at IS NOT NULL AND expires_at < ?)
                   OR target_id IN (SELECT id FROM entities WHERE expires_at IS NOT NULL AND expires_at < ?)
                """,
                (now, now),
            )
            await db.execute(
                "DELETE FROM entities WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,),
            )
            await db.commit()

    def _expires_at(self, ent_type: str) -> str | None:
        days = settings.specter.knowledge.default_ttl_days
        if ent_type in {"email", "credential"}:
            days = settings.specter.knowledge.sensitive_ttl_days
        return (datetime.utcnow() + timedelta(days=days)).isoformat()

    async def _summarize_texts(self, facts: list[str]) -> str:
        router = LLMRouter()
        if router.routes:
            prompt = (
                "Summarize the following facts into a concise operational summary.\n\n"
                + "\\n".join(f"- {fact}" for fact in facts)
            )
            try:
                return await router.generate(prompt)
            except Exception:
                pass
        return " | ".join(facts[: settings.specter.knowledge.summary_window])
