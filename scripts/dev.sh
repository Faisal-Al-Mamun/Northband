#!/usr/bin/env bash
# Copy .env if missing, then start the full Docker Compose stack.
# Usage: ./scripts/dev.sh          (foreground)
#        ./scripts/dev.sh -d       (detached)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add an LLM key for real scoring (optional)."
fi

cat <<'EOF'
Northband
  Studio   http://localhost:3000
  API      http://localhost:8000/docs
  Health   http://localhost:8000/health
  Login    demo@northband.app / demo12345

First API image build pulls torch/faster-whisper (several minutes, CPU only, no GPU).
After the API is up:  ./scripts/seed.sh
EOF

exec docker compose up --build "$@"
