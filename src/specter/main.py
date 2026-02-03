from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi.responses import JSONResponse
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

from .brain.orchestrator import Orchestrator
from .config import settings
from .core.logging import configure_logging
from .graph.streaming import StreamCallback
from .knowledge.graph import KnowledgeGraph
from .skills.forge import SkillForge
from .storage import ExecutionStore


class SimpleCallback(StreamCallback):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

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


class SkillForgeRequest(BaseModel):
    description: str


class HealingOverrideRequest(BaseModel):
    execution_id: str
    fix_type: str


class ToolInvokeRequest(BaseModel):
    tool_name: str
    params: dict[str, Any] = {}


configure_logging()
settings.load_yaml()

db_path = "./data/specter.db"
store = ExecutionStore(db_path=db_path)
orchestrator = Orchestrator(store=store)
kg = KnowledgeGraph(db_path=db_path)
forge = SkillForge(orchestrator.skills.register)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await kg.init()
    yield


app = FastAPI(title="Specter", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/webhook/{channel}")
async def receive_message(channel: str, payload: dict[str, Any]) -> JSONResponse:
    callback = SimpleCallback()
    user_text = payload.get("text", "")
    await kg.add_fact(user_text, confidence=0.6)
    result = await orchestrator.run(
        user_text, {"channel": channel, "user_id": payload.get("user_id", "local")}, callback
    )
    return JSONResponse({"result": result, "events": callback.events})


@app.get("/knowledge/search")
async def search_knowledge(q: str, user_id: str) -> JSONResponse:
    result = await kg.query(q)
    return JSONResponse({"user_id": user_id, "results": result})


@app.post("/skills/forge")
async def create_skill(payload: SkillForgeRequest) -> JSONResponse:
    result = await forge.forge(payload.description)
    return JSONResponse(result)


@app.post("/tools/invoke")
async def invoke_tool(payload: ToolInvokeRequest) -> JSONResponse:
    result = await orchestrator.skills.execute(payload.tool_name, payload.params)
    return JSONResponse(result)


@app.get("/executions/{exec_id}")
async def get_execution(exec_id: str) -> JSONResponse:
    result = await store.get_execution(exec_id)
    if result is None:
        return JSONResponse({"error": "not_found", "id": exec_id}, status_code=404)
    return JSONResponse(result)


@app.post("/healing/override")
async def manual_heal(payload: HealingOverrideRequest) -> JSONResponse:
    await store.set_status(payload.execution_id, "healing")
    await store.add_audit(
        payload.execution_id,
        "manual_heal",
        {"fix_type": payload.fix_type},
    )
    return JSONResponse(
        {"execution_id": payload.execution_id, "fix_type": payload.fix_type, "status": "healing"}
    )


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    await websocket.accept()
    await websocket.send_json({"user_id": user_id, "status": "connected"})
    while True:
        data = await websocket.receive_text()
        callback = SimpleCallback()
        await kg.add_fact(data, confidence=0.6)
        result = await orchestrator.run(data, {"user_id": user_id}, callback)
        await websocket.send_json({"result": result, "events": callback.events})


def run() -> None:
    import uvicorn

    uvicorn.run("specter.main:app", host="0.0.0.0", port=8000, reload=False)
