#!/usr/bin/env bash
# One-command demo: start Docker, migrate, seed demo data, print URLs and logins.
# Passwords are read from .env and are never printed.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required to run the demo" >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env from .env.example"
fi

set_env_value() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { found = 0 }
    $0 ~ "^" key "=" { print key "=" value; found = 1; next }
    { print }
    END { if (!found) print key "=" value }
  ' .env > "$tmp"
  mv "$tmp" .env
  chmod 600 .env
}

ensure_demo_password() {
  local key="$1" current generated
  current="$(awk -F= -v key="$key" '$1 == key { print substr($0, index($0, "=") + 1) }' .env | tail -n 1)"
  if [ -z "$current" ]; then
    generated="$(head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-32)"
    set_env_value "$key" "$generated"
    echo "Generated $key in .env (value not printed)"
  fi
}

ensure_demo_password DEMO_ADMIN_1_PASSWORD
ensure_demo_password DEMO_ADMIN_2_PASSWORD

echo "Starting the demo stack (the first build can take a few minutes)..."
docker compose up --build -d

wait_for_healthy() {
  local service="$1" timeout="${2:-300}" elapsed=0 cid status
  while [ "$elapsed" -lt "$timeout" ]; do
    cid="$(docker compose ps -q "$service" 2>/dev/null || true)"
    if [ -n "$cid" ]; then
      status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
      if [ "$status" = "healthy" ]; then
        return 0
      fi
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  echo "ERROR: $service did not become healthy within ${timeout}s" >&2
  docker compose ps >&2 || true
  exit 1
}

wait_for_healthy api 300
wait_for_healthy web 300

echo "Applying database migrations..."
docker compose exec -T -e PYTHONPATH=/app api alembic upgrade head

echo "Seeding demo organization, admins, templates, group, campaigns and events..."
docker compose exec -T -e APP_ENV=development -e PYTHONPATH=/app api python -m app.scripts.seed_dev
docker compose exec -T -e APP_ENV=development -e PYTHONPATH=/app api python -m app.scripts.seed_demo

cat <<'EOF'

Demo stack is ready.
  Frontend:    http://127.0.0.1:3000
  API health:  http://127.0.0.1:8000/health
  Mailpit:     http://127.0.0.1:8025

Demo admin emails (passwords are in .env and are never printed):
  demo-admin-1@example.test
  demo-admin-2@example.test

Seeded demo data:
  Organization: Demo Organization (demo-org)
  Group:        Demo Finance Team (8 sandbox targets)
  Campaigns:    Demo awareness: invoice review (completed)
                Demo awareness: travel policy update (running)
EOF
