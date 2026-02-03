from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

import aiosqlite


class KnowledgeGraph:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            with open("migrations/001_init.sql", encoding="utf-8") as f:
                await db.executescript(f.read())
            await db.commit()

    async def add_fact(self, statement: str, confidence: float = 1.0) -> str:
        fact_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO entities (id, type, name, attributes, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (fact_id, "fact", statement[:128], json.dumps({"raw": statement}), now),
            )
            entities = self._extract_entities(statement)
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

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
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
            "INSERT INTO entities (id, type, name, attributes, created_at) VALUES (?, ?, ?, ?, ?)",
            (ent_id, ent_type, name, json.dumps({}), now),
        )
        return ent_id
