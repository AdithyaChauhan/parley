#!/bin/bash
# Copies the server's .env into AWS Parameter Store, once (D31). Each line
# KEY=value becomes an encrypted parameter /parley/prod/KEY. Run it on the
# server, in the repo folder, while Terraform's allow_secret_upload is true:
#   bash deploy/aws/store-secrets.sh
# No value is ever shown on screen, and none leaves AWS: the server talks to
# Parameter Store directly, with its own role.
set -euo pipefail

REGION="${AWS_REGION:-ap-south-1}"

# Run from the repo folder, wherever the script was called from.
cd "$(dirname "$0")/../.."

if ! command -v aws >/dev/null; then
  echo "No AWS CLI on this server. Install it once with: sudo snap install aws-cli --classic" >&2
  exit 1
fi

# The settings only: no comments, no empty lines.
settings() {
  grep -v -e '^#' -e '^$' .env
}

stored=0
while IFS= read -r line; do
  key="${line%%=*}"
  value="${line#*=}"
  # The value goes in through stdin (file:///dev/stdin), not on the command
  # line, so it never shows up in the server's process list either.
  printf '%s' "$value" | aws ssm put-parameter --region "$REGION" \
    --name "/parley/prod/$key" --type SecureString --overwrite \
    --value file:///dev/stdin >/dev/null
  echo "stored /parley/prod/$key"
  stored=$((stored + 1))
done < <(settings)

# Proof: read everything back and compare with .env, without printing either.
from_aws() {
  aws ssm get-parameters-by-path --region "$REGION" --path /parley/prod \
    --with-decryption --query 'Parameters[].[Name,Value]' --output text \
    | sed -e 's|^/parley/prod/||' -e 's|\t|=|'
}

if diff <(settings | sort) <(from_aws | sort) >/dev/null; then
  echo "Done: $stored settings stored, and Parameter Store matches .env exactly."
else
  echo "Stored $stored settings, but Parameter Store does NOT match .env. Nothing was changed on the server; tell Claude Code." >&2
  exit 1
fi
