#!/usr/bin/env bash
# Brings all of Parley up on a local Kubernetes cluster, from nothing, at
# http://localhost:8090 (D35). Run it again after a code change: the same steps
# roll out the new version, one backend pod at a time.
#
#   bash deploy/k8s/up.sh              tag = the current commit
#   PARLEY_TAG=try1 bash deploy/k8s/up.sh   tag = your own name
set -euo pipefail

cd "$(dirname "$0")/../.."

CLUSTER=parley
# Always this cluster, whatever kubectl's current one is.
KUBECTL=(kubectl --context "kind-$CLUSTER")
TIMEOUT=300s

command -v kind > /dev/null || { echo "kind isn't installed. See docs/kubernetes.md." >&2; exit 1; }
command -v kubectl > /dev/null || { echo "kubectl isn't installed. See docs/kubernetes.md." >&2; exit 1; }

STARTED=$SECONDS
step() { echo "== $1 (at $((SECONDS - STARTED)) s)"; }

TAG="${PARLEY_TAG:-$(git rev-parse --short HEAD)}"
step "Version $TAG"

if kind get clusters | tr -d '\r' | grep -qx "$CLUSTER"; then
  step "Cluster $CLUSTER is already there"
else
  step "Creating cluster $CLUSTER"
  kind create cluster --config deploy/k8s/kind-config.yaml
fi

# The same images as Compose, tagged with the commit (D27, D35).
step "Building images"
docker build --quiet --tag "parley-backend:$TAG" --build-arg "APP_VERSION=$TAG" backend
docker build --quiet --tag "parley-web:$TAG" frontend

step "Loading images into the cluster (there's no registry)"
kind load docker-image --name "$CLUSTER" "parley-backend:$TAG" "parley-web:$TAG"

# Helper images already on this machine go in too, so a new cluster doesn't
# download them again. `kind load` can't take these: on Docker's newer image store
# they list every platform, and only one is here. Any image that isn't here, the
# cluster downloads by itself.
PLATFORM="linux/$(docker version --format '{{.Server.Arch}}' | tr -d '\r')"
for image in postgres:17.11 redis:8.10.2 rabbitmq:4.3.7-management dxflrs/garage:v2.4.1; do
  if docker image inspect "$image" > /dev/null 2>&1 && ! docker exec "$CLUSTER-control-plane" crictl inspecti "$image" > /dev/null 2>&1; then
    echo "Loading $image"
    docker save --platform "$PLATFORM" "$image" \
      | docker exec -i "$CLUSTER-control-plane" ctr --namespace=k8s.io images import --snapshotter=overlayfs - > /dev/null \
      || echo "(couldn't load $image: the cluster will download it)"
  fi
done

# Kustomize only reads files inside its own folder, so the store's settings are
# copied in, to stay the same as Compose's (D38). The copy is git-ignored.
cp deploy/storage/garage.toml deploy/k8s/garage.toml

# Rendered once, with this version's tag in place of :dev.
RENDERED=$("${KUBECTL[@]}" kustomize deploy/k8s | sed -e "s/parley-backend:dev/parley-backend:$TAG/" -e "s/parley-web:dev/parley-web:$TAG/")

apply_stage() {
  printf '%s\n' "$RENDERED" | "${KUBECTL[@]}" apply -f - -l "stage=$1"
}

step "Namespace and secrets"
"${KUBECTL[@]}" apply -f deploy/k8s/namespace.yaml
bash deploy/k8s/make-secret.sh .env | "${KUBECTL[@]}" apply -f -

step "Helpers: PostgreSQL, Redis, RabbitMQ, file store"
apply_stage helpers
for helper in postgres redis rabbitmq storage; do
  "${KUBECTL[@]}" -n parley rollout status "statefulset/$helper" --timeout="$TIMEOUT"
done

# Before the backends start or roll, so two copies never migrate at once (D27).
step "Migrating the database, and getting the file store ready"
"${KUBECTL[@]}" -n parley delete job migrate storage-setup --ignore-not-found
apply_stage migrate
if ! "${KUBECTL[@]}" -n parley wait --for=condition=complete job/migrate --timeout="$TIMEOUT"; then
  "${KUBECTL[@]}" -n parley logs job/migrate --tail=50 || true
  echo "The migration didn't finish." >&2
  exit 1
fi
if ! "${KUBECTL[@]}" -n parley wait --for=condition=complete job/storage-setup --timeout="$TIMEOUT"; then
  "${KUBECTL[@]}" -n parley logs job/storage-setup --tail=50 || true
  echo "The file store's setup didn't finish." >&2
  exit 1
fi

step "Parley: backend, worker, web"
apply_stage app
for app in backend worker web; do
  "${KUBECTL[@]}" -n parley rollout status "deployment/$app" --timeout="$TIMEOUT"
done

"${KUBECTL[@]}" -n parley get pods
echo
echo "Parley is up at http://localhost:8090 (version $TAG), in $((SECONDS - STARTED)) s"
