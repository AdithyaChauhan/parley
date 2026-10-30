#!/bin/bash
# Runs once, as root, on the server's first boot (EC2 "user data").
# Installs Docker and the Compose plugin from Docker's own repo, which has a
# newer Compose than Ubuntu's (docker-compose.prod.yml needs 2.24+ for !reset).
# Its output goes to /var/log/cloud-init-output.log on the server.
# These are Docker's official steps for Ubuntu; deploy/server/setup.sh skips
# them when Docker is already here.
set -euo pipefail

# On first boot Ubuntu runs its own automatic updates, which hold apt's lock.
# DPkg::Lock::Timeout=300: wait up to 5 minutes for it instead of failing.
apt-get -o DPkg::Lock::Timeout=300 update
apt-get -o DPkg::Lock::Timeout=300 install -y ca-certificates curl

# Docker's signing key, so apt trusts packages from Docker's repo.
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Docker's repo for this Ubuntu version (24.04 = "noble").
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get -o DPkg::Lock::Timeout=300 update
apt-get -o DPkg::Lock::Timeout=300 install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
