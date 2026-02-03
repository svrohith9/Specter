from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .agent import AgentRuntime, build_agent_runtime
from .config import settings
from .core.logging import configure_logging
from .graph.models import ExecutionGraph
from .graph.streaming import StreamCallback


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


class SkillInstallRequest(BaseModel):
    name: str
    description: str


class ToolListResponse(BaseModel):
    tools: list[str]


class SkillRunRequest(BaseModel):
    name: str
    params: dict[str, Any] = {}


class SkillListResponse(BaseModel):
    skills: list[str]


configure_logging()
settings.load_yaml()

_agents: dict[str, AgentRuntime] = {}


def get_agent(agent_id: str | None) -> AgentRuntime:
    resolved = agent_id or settings.specter.default_agent
    if resolved not in _agents:
        _agents[resolved] = build_agent_runtime(settings.specter, resolved)
    return _agents[resolved]


@asynccontextmanager
async def lifespan(_: FastAPI):
    for agent_id in settings.specter.agents.keys() or [settings.specter.default_agent]:
        runtime = get_agent(agent_id)
        await runtime.init()
    yield


app = FastAPI(title="Specter", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/webhook/{channel}")
async def receive_message(channel: str, payload: dict[str, Any]) -> JSONResponse:
    callback = SimpleCallback()
    user_text = payload.get("text", "")
    agent = get_agent(payload.get("agent_id"))
    await agent.init()
    await agent.kg.add_fact(user_text, confidence=0.6)
    result = await agent.orchestrator.run(
        user_text,
        {"channel": channel, "user_id": payload.get("user_id", "local")},
        callback,
    )
    return JSONResponse({"result": result, "events": callback.events})


@app.get("/knowledge/search")
async def search_knowledge(q: str, user_id: str) -> JSONResponse:
    agent = get_agent(user_id)
    await agent.init()
    result = await agent.kg.query(q)
    return JSONResponse({"user_id": user_id, "results": result})


@app.post("/skills/forge")
async def create_skill(payload: SkillForgeRequest) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    result = await agent.forge.forge(
        payload.description,
        persist=lambda name, data: agent.orchestrator.skills.persist_template_skill(
            agent.store.db_path, name, data
        ),
    )
    return JSONResponse(result)


@app.post("/tools/invoke")
async def invoke_tool(payload: ToolInvokeRequest) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    result = await agent.orchestrator.skills.execute(payload.tool_name, payload.params)
    return JSONResponse(result)


@app.get("/tools")
async def list_tools() -> ToolListResponse:
    agent = get_agent(None)
    return ToolListResponse(tools=sorted(agent.orchestrator.skills._skills.keys()))


@app.post("/skills/install")
async def install_skill(payload: SkillInstallRequest) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    await agent.orchestrator.skills.persist_template_skill(
        agent.store.db_path, payload.name, {"description": payload.description}
    )
    await agent.orchestrator.skills.load_from_db(agent.store.db_path)
    return JSONResponse({"installed": True, "name": payload.name})


@app.get("/skills")
async def list_skills() -> SkillListResponse:
    agent = get_agent(None)
    await agent.init()
    return SkillListResponse(skills=agent.orchestrator.skills.list())


@app.post("/skills/run")
async def run_skill(payload: SkillRunRequest) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    result = await agent.orchestrator.skills.execute(payload.name, payload.params)
    return JSONResponse(result)


@app.get("/executions/{exec_id}")
async def get_execution(exec_id: str) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    result = await agent.store.get_execution(exec_id)
    if result is None:
        return JSONResponse({"error": "not_found", "id": exec_id}, status_code=404)
    return JSONResponse(result)


@app.get("/executions")
async def list_executions() -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    result = await agent.store.list_executions()
    return JSONResponse({"executions": result})


@app.post("/executions/{exec_id}/replay")
async def replay_execution(exec_id: str) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    existing = await agent.store.get_execution(exec_id)
    if existing is None:
        return JSONResponse({"error": "not_found", "id": exec_id}, status_code=404)
    graph = ExecutionGraph.from_dict(existing["graph"])
    callback = SimpleCallback()
    result = await agent.orchestrator.executor.execute(graph, callback)
    return JSONResponse({"replayed": True, "result": result, "events": callback.events})


@app.post("/healing/override")
async def manual_heal(payload: HealingOverrideRequest) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    await agent.store.set_status(payload.execution_id, "healing")
    await agent.store.add_audit(
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
        agent = get_agent(user_id)
        await agent.init()
        await agent.kg.add_fact(data, confidence=0.6)
        result = await agent.orchestrator.run(data, {"user_id": user_id}, callback)
        await websocket.send_json({"result": result, "events": callback.events})


@app.get("/ui")
async def ui() -> HTMLResponse:
    agent = get_agent(None)
    await agent.init()
    items = await agent.store.list_executions()
    rows = "\n".join(
        f"<tr><td>{i['id']}</td><td>{i['status']}</td><td>{i['intent']}</td></tr>"
        for i in items
    )
    html = f"""
    <html>
      <head><title>Specter UI</title></head>
      <body>
        <h2>Specter Executions</h2>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>ID</th><th>Status</th><th>Intent</th></tr>
          {rows}
        </table>
      </body>
    </html>
    """
    return HTMLResponse(html)


def run() -> None:
    import uvicorn

    uvicorn.run("specter.main:app", host="0.0.0.0", port=8000, reload=False)
