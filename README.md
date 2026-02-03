# Specter
Execution-first autonomous agent with parallel DAG execution, self-healing, structured memory, and presence intelligence.

## Status
Early scaffold. Core architecture is in place; functional integrations are being wired in incrementally.

## Features
- Parallel execution graphs (DAG-based)
- Self-healing error handling (strategy-based)
- Structured knowledge graph memory (SQLite)
- Presence intelligence for confirmation vs autonomy
- FastAPI webhooks + WebSocket streaming

## Quick Start

```bash
poetry install
poetry run uvicorn specter.main:app --reload
```

Or with Docker:

```bash
docker-compose up --build
```

## Configuration
- `config.yaml` controls execution, LLM routing, and channel settings.
- `.env.example` shows required environment variables.

## API
- `POST /webhook/{channel}`
- `WS /ws/{user_id}`
- `GET /knowledge/search`
- `POST /skills/forge`
- `GET /executions/{id}`
- `POST /healing/override`
- `GET /health`

## Development

```bash
poetry run pytest
poetry run ruff check .
```

## License
MIT
