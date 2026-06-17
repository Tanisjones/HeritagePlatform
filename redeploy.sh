#!/usr/bin/env bash
#
# redeploy.sh — pull the latest code and redeploy the production stack.
#
# Run on the server, from the repo root:
#     cd ~/HeritagePlatform && ./redeploy.sh
#
# It pulls main, rebuilds the images, restarts the stack, and prunes dangling
# images scoped to THIS project. Database migrations and collectstatic run
# automatically inside the backend entrypoint on every start. Safe to re-run; it
# stops on the first error.

set -euo pipefail

cd "$(dirname "$0")"

# Pin the compose project name so the scoped image prune below is reliable
# regardless of the clone directory name.
PROJECT="heritageplatform"
COMPOSE="docker compose -p ${PROJECT} -f docker-compose.prod.yml --env-file .env.prod"

# --- preflight ---------------------------------------------------------------
if [ ! -f .env.prod ]; then
    echo "ERROR: .env.prod not found. Copy .env.prod.example to .env.prod and fill it in." >&2
    exit 1
fi

echo "==> Current commit: $(git rev-parse --short HEAD)"

# --- pull --------------------------------------------------------------------
echo "==> Fetching latest from origin/main ..."
git fetch --quiet origin main
BEFORE=$(git rev-parse HEAD)
AFTER=$(git rev-parse origin/main)

if [ "$BEFORE" = "$AFTER" ]; then
    echo "==> Already up to date ($(git rev-parse --short HEAD)). Rebuilding anyway to pick up any local changes."
else
    echo "==> Updating $(git rev-parse --short "$BEFORE") -> $(git rev-parse --short "$AFTER"):"
    git --no-pager log --oneline "$BEFORE".."$AFTER" | sed 's/^/      /'
    git merge --ff-only origin/main
fi

# --- build & restart ---------------------------------------------------------
# The backend entrypoint applies migrations + collectstatic on startup.
echo "==> Building and (re)starting containers ..."
$COMPOSE up -d --build

# --- cleanup -----------------------------------------------------------------
# Only remove THIS project's now-dangling images. A blanket `docker image prune`
# would also drop dangling images other stacks on this host depend on, forcing
# their containers to restart (and breaking sibling apps). Scope it tightly.
echo "==> Removing this project's dangling images ..."
docker image prune -f \
    --filter "label=com.docker.compose.project=${PROJECT}" >/dev/null 2>&1 || true

# --- status ------------------------------------------------------------------
echo "==> Done. Stack status:"
$COMPOSE ps

echo
echo "==> Live at https://heritageplatform.ddns.net"
