#!/bin/bash
# Puts the newest code of this server's branch live (D29, D30). In the repo folder:
#   bash deploy/server/deploy.sh        pull, rebuild what changed, restart it
#   bash deploy/server/deploy.sh web    frontend or Nginx only: the backend copies
#                                       keep running (D28)
# To follow a different branch (for example main, after a merge):
#   git switch main && bash deploy/server/deploy.sh
set -euo pipefail

# Run from the repo folder, wherever the script was called from.
cd "$(dirname "$0")/../.."

compose() {
  docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app "$@"
}

echo "== Pulling the newest code of $(git branch --show-current)"
# --ff-only: only move forward. If the server's copy was edited by hand, stop
# instead of mixing the two.
git pull --ff-only

if [ "${1:-}" != "web" ]; then
  echo "== Rebuilding and restarting what changed"
  # Only services whose image or settings changed are recreated. migrate runs
  # again first (it only changes something when there's a new migration).
  # A changed backend restarts both copies together: live lines drop for a few
  # seconds and the apps reconnect by themselves (D21).
  # --remove-orphans: remove containers of services that no longer exist (D28).
  compose up -d --build --remove-orphans
fi

echo "== Rebuilding and restarting web (Nginx)"
# Always recreated: nginx.prod.conf is mounted as a single file, and a running
# container keeps the old file after `git pull` replaces it. --no-deps: leave
# the backend copies alone (D28).
compose up -d --no-deps --build --force-recreate web

# Old image layers from earlier builds would slowly fill the 20 GB disk.
# This only removes unused, unnamed ones.
docker image prune -f

compose ps
