from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    tool_name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    prompt: Optional[str] = None
    condition: Optional[str] = None


class Node(BaseModel):
    id: str
    type: str  # tool|llm|condition|human_confirm
    spec: NodeSpec = Field(default_factory=NodeSpec)
    deps: List[str] = Field(default_factory=list)
    error_strategy: str = "retry"
    timeout_seconds: int = 30
    stream_output: bool = False


class ExecutionPlan(BaseModel):
    intent_summary: str
    confidence: float
    nodes: List[Node]


class ExecutionGraph(BaseModel):
    nodes: List[Node]
    max_parallel: int = 10

    def node_by_id(self) -> Dict[str, Node]:
        return {n.id: n for n in self.nodes}

    def topological_sort(self) -> List[Node]:
        nodes = self.node_by_id()
        indeg = {n.id: 0 for n in self.nodes}
        for n in self.nodes:
            for d in n.deps:
                indeg[n.id] += 1
        queue = [nid for nid, deg in indeg.items() if deg == 0]
        ordered: List[Node] = []
        while queue:
            nid = queue.pop(0)
            ordered.append(nodes[nid])
            for n in self.nodes:
                if nid in n.deps:
                    indeg[n.id] -= 1
                    if indeg[n.id] == 0:
                        queue.append(n.id)
        return ordered
