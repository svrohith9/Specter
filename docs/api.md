# API

## Health
- `GET /health` → `{ "status": "ok" }`

## Webhooks
- `POST /webhook/{channel}`
  - Accepts message payloads
  - Returns execution results

## Knowledge
- `GET /knowledge/search?q=...&user_id=...`
  - Returns recent knowledge graph results
- `GET /knowledge/entities?q=...&user_id=...`
  - Returns entity nodes and relation hints
- `GET /knowledge/summary?user_id=...`
  - Returns recent memory summaries
- `POST /knowledge/summarize?user_id=...`
  - Creates a new summary from recent facts
- `POST /knowledge/cleanup?user_id=...`
  - Clears expired entities and relations
- `GET /knowledge/entities/list?user_id=...&ent_type=...&search=...&limit=...`
  - List entities with filters

## Skills
- `POST /skills/forge`
  - Create a lightweight template skill
- `POST /skills/install`
  - Install a template skill from JSON
- `GET /skills`
  - List skills
- `POST /skills/run`
  - Execute a skill by name

## Tools
- `POST /tools/invoke`
  - Invoke a registered tool (e.g., `calculate`, `web_fetch`)
- `GET /tools`
  - List registered tools

## Executions
- `GET /executions/{id}`
  - Stored execution record
- `GET /executions`
  - List recent executions
- `POST /executions/{id}/replay`
  - Replay a stored execution graph

## Agents
- `GET /agents`
  - List registered agents and roles
- `POST /agents/delegate`
  - Delegate a task to a specific agent or role

## Healing
- `POST /healing/override`
  - Manual healing override (stub)

## Streaming
- `WS /ws/{user_id}`
  - Real-time execution streaming

## UI
- `GET /ui`
  - Minimal local dashboard (HTML)
