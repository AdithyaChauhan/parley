#!/bin/bash
# Gets a fresh Linux server (Ubuntu or Debian) ready for Parley (D29, D30).
# Run it once, as a normal user that can sudo, with the branch to clone
# (default: main):
#   curl -fsSL https://raw.githubusercontent.com/AdithyaChauhan/parley/main/deploy/server/setup.sh | bash -s -- [branch]
# Safe to run again: each part is skipped when it's already done.
set -euo pipefail

BRANCH="${1:-main}"
REPO="${PARLEY_REPO:-https://github.com/AdithyaChauhan/parley.git}"
DIR="${PARLEY_DIR:-/opt/parley}"
# Who is running this. Not $USER: a Session Manager shell may not set it.
ME="$(id -un)"

# 1. Docker and the Compose plugin, from Docker's own repo (Ubuntu's Compose is
#    too old for !reset). On AWS, user_data already did this.
if command -v docker >/dev/null; then
  echo "Docker: already installed ($(docker --version))"
else
  echo "Docker: installing..."
  . /etc/os-release   # gives $ID (ubuntu or debian) and $VERSION_CODENAME
  sudo apt-get -o DPkg::Lock::Timeout=300 update
  sudo apt-get -o DPkg::Lock::Timeout=300 install -y ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get -o DPkg::Lock::Timeout=300 update
  sudo apt-get -o DPkg::Lock::Timeout=300 install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# Let this user run docker without sudo (takes effect at the next log-in).
# Note: the docker group is as powerful as root, so only trusted users join it.
sudo usermod -aG docker "$ME"

# 2. A 2 GB swap file: spare memory on the disk. A 2 GB server runs Parley in
#    about 1 GB, but building the images briefly needs more (D30).
if swapon --show | grep -q .; then
  echo "Swap: already on"
else
  echo "Swap: adding 2 GB..."
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile       # only root may read it: it can hold bits of memory
  sudo mkswap /swapfile
  sudo swapon /swapfile
  # Turn it on again after every reboot.
  echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
fi

# 3. The code.
if [ -d "$DIR/.git" ]; then
  echo "Code: already in $DIR (deploy/server/deploy.sh updates it)"
else
  echo "Code: cloning branch $BRANCH into $DIR..."
  sudo install -d -o "$ME" -g "$ME" "$DIR"
  git clone --branch "$BRANCH" "$REPO" "$DIR"
fi

echo
echo "Done. Next (see deploy/README.md):"
echo "  1. exit, and start a new session (so the docker group applies)"
echo "  2. cd $DIR && cp deploy/server/.env.prod.example .env && chmod 600 .env && nano .env"
echo "  3. bash deploy/server/first-cert.sh <your-domain> <your-email>"
