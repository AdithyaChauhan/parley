#!/usr/bin/env bash
# Prints the parley-secrets Secret, made from .env, for `kubectl apply -f -` (D35).
# It writes no file and passes no secret as a command argument. Don't run it on
# its own in a terminal: the output is only base64, which anyone can read back.
set -euo pipefail

ENV_FILE="${1:-.env}"
[ -f "$ENV_FILE" ] || { echo "No $ENV_FILE. Copy .env.example to .env first." >&2; exit 1; }

# One value from .env. tr: on Windows, the file may have Windows line endings.
value() {
  tr -d '\r' < "$ENV_FILE" | grep -E "^$1=" | tail -n 1 | cut -d= -f2- || true
}

# Secret values are stored as base64, which is an encoding, not encryption.
entry() {
  printf '  %s: %s\n' "$1" "$(printf '%s' "$2" | base64 | tr -d '\n')"
}

POSTGRES_DB=$(value POSTGRES_DB)
POSTGRES_USER=$(value POSTGRES_USER)
POSTGRES_PASSWORD=$(value POSTGRES_PASSWORD)
RABBITMQ_USER=$(value RABBITMQ_USER)
RABBITMQ_PASSWORD=$(value RABBITMQ_PASSWORD)
JWT_SECRET=$(value JWT_SECRET)

for name in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD RABBITMQ_USER RABBITMQ_PASSWORD JWT_SECRET; do
  [ -n "${!name}" ] || { echo "$name is missing from $ENV_FILE" >&2; exit 1; }
done

cat <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: parley-secrets
  namespace: parley
type: Opaque
data:
EOF
entry POSTGRES_DB "$POSTGRES_DB"
entry POSTGRES_USER "$POSTGRES_USER"
entry POSTGRES_PASSWORD "$POSTGRES_PASSWORD"
entry RABBITMQ_USER "$RABBITMQ_USER"
entry RABBITMQ_PASSWORD "$RABBITMQ_PASSWORD"
entry JWT_SECRET "$JWT_SECRET"
entry VAPID_PRIVATE_KEY "$(value VAPID_PRIVATE_KEY)"
entry VAPID_PUBLIC_KEY "$(value VAPID_PUBLIC_KEY)"
entry VAPID_SUBJECT "$(value VAPID_SUBJECT)"
# The two addresses with a password inside. Built here with the cluster's own
# names, not copied from .env, which points at the laptop. Those passwords use
# only letters and numbers, so they're safe in an address (D27).
entry DATABASE_URL "postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB"
entry RABBITMQ_URL "amqp://$RABBITMQ_USER:$RABBITMQ_PASSWORD@rabbitmq:5672/%2F"
