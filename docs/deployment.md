# Deployment

## Local (Poetry)
```bash
poetry install
poetry run uvicorn specter.main:app --reload
```

## Local UI (Next.js)
```bash
cd web
npm install
cp .env.local.example .env.local
npm run dev
```

## Docker
```bash
docker-compose up --build
```

## Notes
- Uses SQLite in `./data/`
- Configure env vars via `.env` or `config.yaml`
