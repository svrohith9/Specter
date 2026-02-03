from __future__ import annotations

from dataclasses import dataclass, field

from .brain.orchestrator import Orchestrator
from .config import AgentConfig, SpecterConfig
from .core.security import ToolPolicy, load_tool_policy
from .knowledge.graph import KnowledgeGraph
from .skills.forge import SkillForge
from .storage import ExecutionStore


@dataclass
class AgentRuntime:
    agent_id: str
    store: ExecutionStore
    kg: KnowledgeGraph
    orchestrator: Orchestrator
    forge: SkillForge
    policy: ToolPolicy
    initialized: bool = field(default=False)

    async def init(self) -> None:
        if self.initialized:
            return
        await self.kg.init()
        await self.orchestrator.skills.load_from_db(self.store.db_path)
        self.initialized = True


def resolve_agent_config(config: SpecterConfig, agent_id: str) -> AgentConfig | None:
    return config.agents.get(agent_id)


def resolve_agent_by_role(config: SpecterConfig, role: str) -> str | None:
    for agent_id, agent_cfg in config.agents.items():
        if agent_cfg.role == role:
            return agent_id
    return None


def resolve_db_path(config: SpecterConfig, agent_id: str) -> str:
    agent_cfg = resolve_agent_config(config, agent_id)
    if agent_cfg and agent_cfg.db_path:
        return agent_cfg.db_path
    return f"{config.data_dir}/specter_{agent_id}.db"


def build_agent_runtime(config: SpecterConfig, agent_id: str) -> AgentRuntime:
    agent_cfg = resolve_agent_config(config, agent_id)
    db_path = resolve_db_path(config, agent_id)
    policy = load_tool_policy(agent_cfg.security if agent_cfg else config.security)
    store = ExecutionStore(db_path=db_path)
    kg = KnowledgeGraph(db_path=db_path)
    orchestrator = Orchestrator(store=store, policy=policy)
    forge = SkillForge(orchestrator.skills.register)
    return AgentRuntime(
        agent_id=agent_id,
        store=store,
        kg=kg,
        orchestrator=orchestrator,
        forge=forge,
        policy=policy,
    )
