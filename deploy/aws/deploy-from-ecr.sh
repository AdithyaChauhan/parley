#!/bin/bash
# Puts one Parley version live from ECR (AWS only, D31). The parley-deploy SSM
# document checks out that commit, then runs this as the repo's owner:
#   bash deploy/aws/deploy-from-ecr.sh <tag>        e.g. a410b04
# The backend copies restart one at a time, so live lines move to the other
# copy and chats keep working. On any other server, use deploy/server/deploy.sh.
set -euo pipefail

TAG="${1:?Usage: deploy-from-ecr.sh <tag>}"
REGION="${AWS_REGION:-ap-south-1}"

# Run from the repo folder, wherever the script was called from.
cd "$(dirname "$0")/../.."

if ! command -v aws >/dev/null; then
  echo "No AWS CLI on this server. Install it once with: sudo snap install aws-cli --classic" >&2
  exit 1
fi

# Compose reads these two in deploy/aws/docker-compose.ecr.yml.
export APP_TAG="$TAG"
ECR_REGISTRY="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$REGION.amazonaws.com"
export ECR_REGISTRY

compose() {
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    -f deploy/aws/docker-compose.ecr.yml --profile app "$@"
}

echo "== 1/6 Secrets: Parameter Store -> .env"
# Written next to .env, then moved over it in one step, so .env is never half
# written. mktemp makes the file readable by its owner only (600).
NEW_ENV="$(mktemp .env.new.XXXXXX)"
trap 'rm -f "$NEW_ENV"' EXIT
aws ssm get-parameters-by-path --region "$REGION" --path /parley/prod \
  --with-decryption --query 'Parameters[].[Name,Value]' --output text \
  | sed -e 's|^/parley/prod/||' -e 's|\t|=|' > "$NEW_ENV"
# Something went wrong if the main secret is missing: keep the old .env.
if ! grep -q '^JWT_SECRET=' "$NEW_ENV"; then
  echo "Parameter Store gave no JWT_SECRET: keeping the old .env and stopping." >&2
  exit 1
fi
mv "$NEW_ENV" .env
echo "$(grep -c . .env) settings written to .env (600)"

echo "== 2/6 Images: $TAG from ECR"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null
# web restarts only when something it's built from changed since the running
# version (D31): it drops every live line at once. A web that wasn't built by
# ECR yet (the first time), or a commit git can't compare, counts as changed.
RUNNING_WEB="$(docker inspect --format '{{.Config.Image}}' "$(compose ps -q web)" 2>/dev/null || true)"
OLD_TAG="${RUNNING_WEB##*:}"
if [[ "$RUNNING_WEB" == "$ECR_REGISTRY/parley-web:"* ]] \
  && git diff --quiet "$OLD_TAG" "$TAG" -- frontend deploy/server/nginx.prod.conf \
    docker-compose.yml docker-compose.prod.yml deploy/aws/docker-compose.ecr.yml; then
  WEB=no
else
  WEB=yes
fi
SERVICES=(migrate backend_a backend_b worker)
[ "$WEB" = yes ] && SERVICES+=(web)
compose pull --quiet "${SERVICES[@]}"

echo "== 3/6 Helpers: restarted only if their settings changed"
compose up -d --wait db redis rabbitmq certbot

echo "== 4/6 Tables: migrate"
# Changes must work for the old copy too, which runs on the new tables for a
# moment: add in one deploy, remove in a later one (D31).
compose run --rm --no-deps migrate

echo "== 5/6 Backend copies, one at a time"
compose up -d --no-deps --wait --wait-timeout 120 backend_a
# backend_a has a new address. Nginx looks names up again every 10 s (D28):
# until then, only backend_b is reachable, so it must not stop yet.
echo "backend_a is healthy. Waiting 15 s for Nginx to find it..."
sleep 15
compose up -d --no-deps --wait --wait-timeout 120 backend_b
compose up -d --no-deps worker

echo "== 6/6 web"
if [ "$WEB" = yes ]; then
  # --force-recreate: nginx.prod.conf is mounted as a single file, and a
  # running container keeps the old one (D30).
  compose up -d --no-deps --force-recreate --wait web
else
  echo "frontend, Nginx and Compose files unchanged since $OLD_TAG: web keeps running"
fi

# Images no container uses any more (older versions are still in ECR, for a
# rollback), and the build cache from when the server built its own images.
docker image prune -af >/dev/null
docker builder prune -af >/dev/null

compose ps
echo "Done: $TAG is live."
