# Specter

![CI](https://github.com/svrohith9/Specter/actions/workflows/ci.yml/badge.svg)
![Release](https://github.com/svrohith9/Specter/actions/workflows/release.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

Execution-first autonomous agent with parallel DAG execution, self-healing, structured memory, and presence intelligence.

## Status
Production-oriented core is live. The system persists executions, supports a tool gateway, and provides a local UI.

## Architecture
![Specter architecture](docs/architecture.svg)
![Specter pipeline](docs/pipeline.svg)

## Features
- Parallel execution graphs (DAG-based)
- Self-healing error handling (strategy-based)
- Structured knowledge graph memory (SQLite)
- Presence intelligence for confirmation vs autonomy
- FastAPI webhooks + WebSocket streaming
- Tool invocation gateway with policy allow/deny
- Local CLI for runs and execution replay
 - Local dashboard and Next.js control UI

## Quick Start

```bash
poetry install
poetry run uvicorn specter.main:app --reload
```

CLI example:
```bash
specter-cli run "Summarize today’s tasks"
specter-cli tools
specter-cli exec-list
```

## Web UI (Next.js)

```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000` to interact with Specter.

Or with Docker:

```bash
docker-compose up --build
```

## API Highlights
- `POST /webhook/{channel}` run a task
- `GET /executions` list executions
- `POST /executions/{id}/replay` replay stored execution
- `POST /tools/invoke` call a tool directly
- `GET /tools` list tools
- `GET /ui` minimal local dashboard

## Configuration
- `config.yaml` controls execution, LLM routing, and channel settings.
- `.env.example` shows required environment variables.

## Docs
- `docs/architecture.md`
- `docs/api.md`
- `docs/deployment.md`
- `docs/skills.md`
- `docs/roadmap.md`

## Development

```bash
poetry run pytest
poetry run ruff check .
```

## License
MIT
