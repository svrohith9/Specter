# Contributing

Thanks for your interest in contributing to Specter.

## Development setup

```bash
poetry install
poetry run uvicorn specter.main:app --reload
```

## Code style
- Python 3.12
- Ruff for linting
- Keep functions small and testable

## Testing

```bash
poetry run pytest
```

## Pull requests
- Add or update tests where reasonable
- Update documentation if behavior changes
- Keep PRs focused and scoped
