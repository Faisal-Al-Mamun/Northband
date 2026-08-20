#!/usr/bin/env bash
# Seed demo user + Reading/Listening content. API container must already be running.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose exec -T api python -m app.seed
docker compose exec -T api python -m app.seed_content
