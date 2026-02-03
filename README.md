# Specter
Execution-first autonomous agent with parallel DAG execution, self-healing, structured memory, and presence intelligence.

## Quick Start

```bash
poetry install
poetry run uvicorn specter.main:app --reload
```

Or with Docker:

```bash
docker-compose up --build
```

## Layout

- `src/` core implementation
- `tests/` pytest suite
- `scripts/` utility scripts
- `config.yaml` default configuration

## Notes
- SQLite is the only DB dependency for v1.
- Firejail integration is stubbed; wire to your environment.
