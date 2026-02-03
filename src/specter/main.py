from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

from .brain.orchestrator import Orchestrator
from .config import settings
from .core.logging import configure_logging
from .graph.streaming import StreamCallback
from .knowledge.graph import KnowledgeGraph


class SimpleCallback(StreamCallback):
    def __init__(self) -> None:
        self.events: list[Dict[str, Any]] = []

    async def on_node_start(self, node, progress):
        self.events.append({"event": "start", "node": node.id, "progress": progress.copy()})

    async def on_node_output(self, node, result, progress):
        self.events.append({"event": "output", "node": node.id, "result": result})

    async def on_node_error(self, node, error, progress):
        self.events.append({"event": "error", "node": node.id, "error": str(error)})

    async def on_healing_failed(self, node, fix, progress):
        self.events.append({"event": "healing_failed", "node": node.id, "fix": fix})

    async def on_complete(self, result):
        self.events.append({"event": "complete", "result": result})


configure_logging()
settings.load_yaml()

app = FastAPI(title="Specter", version="0.1.0")

orchestrator = Orchestrator()
kg = KnowledgeGraph(db_path="./data/specter.db")


@app.on_event("startup")
async def on_startup() -> None:
    await kg.init()


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/webhook/{channel}")
async def receive_message(channel: str, payload: Dict[str, Any]) -> JSONResponse:
    callback = SimpleCallback()
    result = await orchestrator.run(payload.get("text", ""), {"channel": channel}, callback)
    return JSONResponse({"result": result, "events": callback.events})


@app.get("/knowledge/search")
async def search_knowledge(q: str, user_id: str) -> JSONResponse:
    result = await kg.query(q)
    return JSONResponse({"user_id": user_id, "results": result})


@app.post("/skills/forge")
async def create_skill(description: str) -> JSONResponse:
    return JSONResponse({"created": False, "description": description})


@app.get("/executions/{exec_id}")
async def get_execution(exec_id: str) -> JSONResponse:
    return JSONResponse({"id": exec_id, "status": "stub"})


@app.post("/healing/override")
async def manual_heal(execution_id: str, fix_type: str) -> JSONResponse:
    return JSONResponse({"execution_id": execution_id, "fix_type": fix_type})


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    await websocket.accept()
    await websocket.send_json({"user_id": user_id, "status": "connected"})
    while True:
        data = await websocket.receive_text()
        callback = SimpleCallback()
        result = await orchestrator.run(data, {"user_id": user_id}, callback)
        await websocket.send_json({"result": result, "events": callback.events})


def run() -> None:
    import uvicorn

    uvicorn.run("specter.main:app", host="0.0.0.0", port=8000, reload=False)
