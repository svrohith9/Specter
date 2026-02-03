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

## Executions
- `GET /executions/{id}`
  - Stub execution trace

## Healing
- `POST /healing/override`
  - Manual healing override (stub)

## Streaming
- `WS /ws/{user_id}`
  - Real-time execution streaming
