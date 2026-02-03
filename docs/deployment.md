# Deployment

## Local (Poetry)
```bash
poetry install
poetry run uvicorn specter.main:app --reload
```

## Docker
```bash
docker-compose up --build
```

## Notes
- Uses SQLite in `./data/`
- Configure env vars via `.env` or `config.yaml`
