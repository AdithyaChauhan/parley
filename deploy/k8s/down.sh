#!/usr/bin/env bash
# Removes the whole local cluster, and its data with it (D35). The Compose stack
# and its dev data have their own volumes, so they aren't touched.
set -euo pipefail

kind delete cluster --name parley

# The images up.sh tagged, one per version. :latest belongs to Compose, so it stays.
docker images --format '{{.Repository}}:{{.Tag}}' \
  | tr -d '\r' \
  | grep -E '^parley-(backend|web):' \
  | grep -v ':latest$' \
  | xargs -r docker rmi > /dev/null || true

# kind's own Docker network, unless another kind cluster still uses it.
if [ -z "$(kind get clusters 2>/dev/null | tr -d '\r')" ]; then
  docker network rm kind > /dev/null 2>&1 || true
fi

echo "The cluster is gone. Compose's dev data wasn't touched."
