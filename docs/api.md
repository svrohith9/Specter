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

## Healing
- `POST /healing/override`
  - Manual healing override (stub)

## Streaming
- `WS /ws/{user_id}`
  - Real-time execution streaming

## UI
- `GET /ui`
  - Minimal local dashboard (HTML)
