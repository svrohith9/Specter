from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .agent import AgentRuntime, build_agent_runtime, resolve_agent_by_role
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
    examples: list[dict[str, Any]] | None = None


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
    details: list[dict[str, Any]] = []


class SkillRunRequest(BaseModel):
    name: str
    params: dict[str, Any] = {}


class SkillListResponse(BaseModel):
    skills: list[str]


class EntityQueryResponse(BaseModel):
    entities: list[dict[str, Any]]


class SummaryResponse(BaseModel):
    summaries: list[dict[str, Any]]


class SummaryCreateResponse(BaseModel):
    summary: dict[str, Any]


class AgentListResponse(BaseModel):
    agents: list[dict[str, Any]]


class MemoryEntitiesResponse(BaseModel):
    entities: list[dict[str, Any]]


class DelegateRequest(BaseModel):
    task: str
    role: str | None = None
    agent_id: str | None = None
    user_id: str | None = None


class ConfigResponse(BaseModel):
    name: str
    default_agent: str
    default_user_id: str
    data_dir: str


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


@app.get("/config")
async def config() -> ConfigResponse:
    return ConfigResponse(
        name=settings.specter.name,
        default_agent=settings.specter.default_agent,
        default_user_id=settings.specter.default_user_id,
        data_dir=settings.specter.data_dir,
    )


@app.post("/webhook/{channel}")
async def receive_message(channel: str, payload: dict[str, Any]) -> JSONResponse:
    callback = SimpleCallback()
    user_text = payload.get("text", "")
    agent = get_agent(payload.get("agent_id"))
    await agent.init()
    await agent.kg.add_fact(user_text, confidence=0.6)
    result = await agent.orchestrator.run(
        user_text,
        {
            "channel": channel,
            "user_id": payload.get("user_id", settings.specter.default_user_id),
        },
        callback,
    )
    return JSONResponse({"result": result, "events": callback.events})


@app.get("/knowledge/search")
async def search_knowledge(q: str, user_id: str) -> JSONResponse:
    agent = get_agent(user_id)
    await agent.init()
    result = await agent.kg.query(q)
    return JSONResponse({"user_id": user_id, "results": result})


@app.get("/knowledge/entities")
async def search_entities(q: str, user_id: str) -> EntityQueryResponse:
    agent = get_agent(user_id)
    await agent.init()
    entities = await agent.kg.query_entities(q)
    return EntityQueryResponse(entities=entities)


@app.get("/knowledge/summary")
async def list_summaries(user_id: str) -> SummaryResponse:
    agent = get_agent(user_id)
    await agent.init()
    summaries = await agent.kg.list_summaries()
    return SummaryResponse(summaries=summaries)


@app.post("/knowledge/summarize")
async def create_summary(user_id: str) -> SummaryCreateResponse:
    agent = get_agent(user_id)
    await agent.init()
    summary = await agent.kg.summarize_recent()
    return SummaryCreateResponse(summary=summary)


@app.post("/knowledge/cleanup")
async def cleanup_memory(user_id: str) -> JSONResponse:
    agent = get_agent(user_id)
    await agent.init()
    await agent.kg.cleanup_expired()
    return JSONResponse({"status": "ok"})


@app.get("/knowledge/entities/list")
async def list_entities(
    user_id: str,
    ent_type: str | None = None,
    limit: int = 50,
    search: str | None = None,
    include_relations: bool = False,
) -> MemoryEntitiesResponse:
    agent = get_agent(user_id)
    await agent.init()
    entities = await agent.kg.list_entities(
        ent_type=ent_type,
        limit=limit,
        search=search,
        include_relations=include_relations,
    )
    return MemoryEntitiesResponse(entities=entities)


@app.get("/agents")
async def list_agents() -> AgentListResponse:
    agents = []
    for agent_id, cfg in settings.specter.agents.items():
        agents.append({"id": agent_id, "role": cfg.role})
    if not agents:
        agents.append({"id": settings.specter.default_agent, "role": "operator"})
    return AgentListResponse(agents=agents)


@app.post("/agents/delegate")
async def delegate_task(payload: DelegateRequest) -> JSONResponse:
    target_id = payload.agent_id
    if not target_id and payload.role:
        target_id = resolve_agent_by_role(settings.specter, payload.role)
    agent = get_agent(target_id)
    await agent.init()
    callback = SimpleCallback()
    result = await agent.orchestrator.run(
        payload.task,
        {"channel": "delegate", "user_id": payload.user_id or "local"},
        callback,
    )
    return JSONResponse({"agent_id": agent.agent_id, "result": result, "events": callback.events})


@app.post("/skills/forge")
async def create_skill(payload: SkillForgeRequest) -> JSONResponse:
    agent = get_agent(None)
    await agent.init()
    result = await agent.forge.forge(
        payload.description,
        examples=payload.examples,
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
    return ToolListResponse(
        tools=sorted(agent.orchestrator.skills._skills.keys()),
        details=agent.orchestrator.skills.list_specs(),
    )


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
