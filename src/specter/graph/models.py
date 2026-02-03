from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    tool_name: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    prompt: str | None = None
    condition: str | None = None


class Node(BaseModel):
    id: str
    type: str  # tool|llm|condition|human_confirm
    spec: NodeSpec = Field(default_factory=NodeSpec)
    deps: list[str] = Field(default_factory=list)
    error_strategy: str = "retry"
    timeout_seconds: int = 30
    stream_output: bool = False


class ExecutionPlan(BaseModel):
    intent_summary: str
    confidence: float
    nodes: list[Node]


class ExecutionGraph(BaseModel):
    nodes: list[Node]
    max_parallel: int = 10

    def node_by_id(self) -> dict[str, Node]:
        return {n.id: n for n in self.nodes}

    def topological_sort(self) -> list[Node]:
        nodes = self.node_by_id()
        indeg = {n.id: 0 for n in self.nodes}
        for n in self.nodes:
            for _d in n.deps:
                indeg[n.id] += 1
        queue = [nid for nid, deg in indeg.items() if deg == 0]
        ordered: list[Node] = []
        while queue:
            nid = queue.pop(0)
            ordered.append(nodes[nid])
            for n in self.nodes:
                if nid in n.deps:
                    indeg[n.id] -= 1
                    if indeg[n.id] == 0:
                        queue.append(n.id)
        return ordered

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionGraph":
        return cls.model_validate(data)
