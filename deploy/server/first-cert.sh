#!/bin/bash
# Gets Parley's first HTTPS certificate, then starts Parley (D30). Run it once,
# in a new session after setup.sh, once .env is filled in:
#   bash deploy/server/first-cert.sh <domain> <email>
#   e.g. bash deploy/server/first-cert.sh parley-adithya.duckdns.org you@example.com
# The domain must already point at this server, and ports 80 and 443 be open.
# After this, the certbot service renews the certificate by itself.
set -euo pipefail

DOMAIN="${1:?Usage: first-cert.sh <domain> <email>}"
EMAIL="${2:?Usage: first-cert.sh <domain> <email>}"

# Run from the repo folder, wherever the script was called from.
cd "$(dirname "$0")/../.."

compose() {
  docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app "$@"
}

# certbot itself, in the official image (the certbot service in docker-compose.prod.yml).
certbot() {
  compose run --rm --no-deps "$@"
}

# Runs after every new or renewed certificate (it's saved with the certificate,
# so renewals run it too). certbot keeps the key readable by root only, and
# Nginx isn't root (D27): this lets Nginx's group (101) read it, and nobody else.
HOOK="chgrp -R 101 /etc/letsencrypt/live /etc/letsencrypt/archive && chmod -R g+rX /etc/letsencrypt/live /etc/letsencrypt/archive"

# The parts every certificate request shares. --cert-name parley: a fixed name,
# so nginx.prod.conf finds it at /etc/letsencrypt/live/parley/ on any domain.
REQUEST=(certonly --non-interactive --standalone --cert-name parley -d "$DOMAIN"
  --email "$EMAIL" --agree-tos --no-eff-email)

# Port 80 must be free for certbot: stop Nginx if it's running (a re-run).
compose stop web

echo "== 1/4 Practice run on Let's Encrypt's test server (saves nothing)"
# -p 80:80: for this one run, certbot itself answers Let's Encrypt on port 80.
certbot -p 80:80 --entrypoint certbot certbot "${REQUEST[@]}" --dry-run

echo "== 2/4 The real certificate"
certbot -p 80:80 --entrypoint certbot certbot "${REQUEST[@]}" --deploy-hook "$HOOK"

echo "== 3/4 Starting Parley (the first build takes a few minutes)"
compose up -d --build

echo "== 4/4 Renewals go through Nginx from now on (webroot), proved by a practice renewal"
# reconfigure does a practice renewal with the new way, and saves it only if it works.
certbot --entrypoint certbot certbot reconfigure --non-interactive --cert-name parley \
  --webroot --webroot-path /var/www/certbot
certbot --entrypoint certbot certbot renew --dry-run

echo
echo "Done: https://$DOMAIN"
