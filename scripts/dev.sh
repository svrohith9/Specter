#!/usr/bin/env bash
set -euo pipefail
poetry run uvicorn specter.main:app --reload
