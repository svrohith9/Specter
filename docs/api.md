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
  - Stub endpoint for skill creation

## Tools
- `POST /tools/invoke`
  - Invoke a registered tool (e.g., `calculate`, `web_fetch`)
- `GET /tools`
  - List registered tools

## Executions
- `GET /executions/{id}`
  - Stub execution trace
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
  - Minimal local dashboard
