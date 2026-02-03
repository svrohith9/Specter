from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite


class ExecutionStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def create_execution(self, user_id: str, intent: str, graph: dict[str, Any]) -> str:
        exec_id = f"exec_{int(datetime.utcnow().timestamp() * 1000)}"
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO executions (id, user_id, intent, graph_json, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (exec_id, user_id, intent, json.dumps(graph), "running", now),
            )
            await db.commit()
        return exec_id

    async def complete_execution(self, exec_id: str, result: dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE executions
                SET status = ?, result = ?, completed_at = ?
                WHERE id = ?
                """,
                ("completed", json.dumps(result), now, exec_id),
            )
            await db.commit()

    async def fail_execution(self, exec_id: str, error: str) -> None:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE executions
                SET status = ?, result = ?, completed_at = ?
                WHERE id = ?
                """,
                ("failed", json.dumps({"error": error}), now, exec_id),
            )
            await db.commit()

    async def set_status(self, exec_id: str, status: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE executions SET status = ? WHERE id = ?",
                (status, exec_id),
            )
            await db.commit()

    async def get_execution(self, exec_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, intent, graph_json, status, result, started_at, completed_at
                FROM executions WHERE id = ?
                """,
                (exec_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "intent": row[2],
                "graph": json.loads(row[3]),
                "status": row[4],
                "result": json.loads(row[5]) if row[5] else None,
                "started_at": row[6],
                "completed_at": row[7],
            }

    async def list_executions(self, limit: int = 20) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, intent, status, started_at, completed_at
                FROM executions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "intent": r[1],
                    "status": r[2],
                    "started_at": r[3],
                    "completed_at": r[4],
                }
                for r in rows
            ]

    async def add_audit(self, exec_id: str, action: str, details: dict[str, Any]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO audit_log (execution_id, action, details)
                VALUES (?, ?, ?)
                """,
                (exec_id, action, json.dumps(details)),
            )
            await db.commit()
