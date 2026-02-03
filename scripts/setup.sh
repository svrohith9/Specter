#!/usr/bin/env bash
set -euo pipefail

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry not found. Install with: pip install poetry"
  exit 1
fi

poetry install
poetry run uvicorn specter.main:app --reload
