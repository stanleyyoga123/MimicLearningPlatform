#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$project_root/.env" ]]; then
  set -a
  source "$project_root/.env"
  set +a
fi
unset GITHUB_TOKEN GH_TOKEN GH_ENTERPRISE_TOKEN GITHUB_REVIEW_TOKEN OPENROUTER_API_KEY
unset GITHUB_APP_ID GITHUB_APP_PRIVATE_KEY_PATH
cd "$project_root/backend"
exec .venv/bin/uvicorn apprenticeship.webhook_app:create_default_webhook_app --factory --host 127.0.0.1 --port "${WEBHOOK_PORT:-8001}"
