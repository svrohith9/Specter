from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

import aiosqlite


class KnowledgeGraph:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            with open("migrations/001_init.sql", "r", encoding="utf-8") as f:
                await db.executescript(f.read())
            await db.commit()

    async def add_fact(self, statement: str, confidence: float = 1.0) -> str:
        entity_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO entities (id, type, name, attributes, created_at) VALUES (?, ?, ?, ?, ?)",
                (entity_id, "concept", statement[:128], json.dumps({"raw": statement}), now),
            )
            await db.commit()
        return entity_id

    async def query(self, question: str, limit: int = 5) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, attributes FROM entities ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                {"id": r[0], "name": r[1], "attributes": json.loads(r[2] or "{}")} for r in rows
            ]
