#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$project_root/.env" ]]; then
  set -a
  source "$project_root/.env"
  set +a
fi
unset GITHUB_TOKEN GH_TOKEN GH_ENTERPRISE_TOKEN GITHUB_REVIEW_TOKEN
cd "$project_root/backend"
exec .venv/bin/uvicorn apprenticeship.main:create_default_app --factory --host 127.0.0.1 --port "${API_PORT:-8000}"
