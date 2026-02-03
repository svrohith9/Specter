# Architecture

## Overview
Specter is an execution-first autonomous agent that converts user requests into parallel execution graphs (DAGs), runs them with a streaming executor, heals failures, and stores structured memory in a SQLite knowledge graph.

## Core flow
1. User message enters via a channel (webhook, WebSocket)
2. Intent compiler generates an execution DAG
3. Executor runs nodes in parallel where possible
4. Self-healing attempts fixes on failures
5. Results are synthesized and streamed back

## Key modules
- `src/specter/graph/` execution DAG, compiler, executor
- `src/specter/healing/` failure diagnosis and strategies
- `src/specter/knowledge/` structured memory (SQLite)
- `src/specter/skills/` tool registry and generation
- `src/specter/presence/` risk + confirmation logic
- `src/specter/channels/` integrations

## Non-goals (v1)
- Multi-tenant federation
- Distributed graph execution
- External DB dependencies
