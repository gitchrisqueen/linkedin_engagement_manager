#!/usr/bin/env bash
# One-time provisioning for a fresh Hostinger VPS (Ubuntu 22.04/24.04).
# Run as root (or with sudo). Idempotent where practical.
#
#   curl -fsSL .../vps_bootstrap.sh | bash   (or scp + run)
#
# After this: place the repo in /opt/lem, create /opt/lem/.env from
# .env.prod.example, then deploy with scripts/deploy.sh.
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="/opt/lem"
REPO_URL="${REPO_URL:-https://github.com/gitchrisqueen/linkedin_engagement_manager.git}"

log() { echo "[bootstrap] $*"; }

[[ "$(id -u)" -eq 0 ]] || { echo "Run as root/sudo." >&2; exit 1; }

log "Installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git ufw gnupg

# --- Docker Engine + Compose v2 plugin (official repo) ---
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker Engine"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

# --- Docker log rotation (the app logs to stdout heavily) ---
log "Configuring Docker log rotation + live-restore"
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" },
  "live-restore": true
}
JSON
systemctl restart docker

# --- Deploy user ---
if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
  log "Creating ${DEPLOY_USER} user"
  useradd -m -s /bin/bash "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

# --- App directory ---
log "Preparing ${APP_DIR}"
mkdir -p "$APP_DIR"
if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

# --- Firewall: only SSH inbound. Cloudflare Tunnel dials OUT, so no 80/443. ---
log "Configuring ufw (SSH only inbound)"
ufw allow OpenSSH
ufw --force enable

# --- SSH hardening ---
log "Hardening SSH (key-only, no root login)"
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd || true

# --- Swap (Selenium/Chrome is memory-hungry) ---
if [[ ! -f /swapfile ]]; then
  log "Creating 4G swapfile"
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

cat <<EOF

[bootstrap] Done. Next steps:
  1. Add the CI deploy public key to /home/${DEPLOY_USER}/.ssh/authorized_keys
  2. cp ${APP_DIR}/.env.prod.example ${APP_DIR}/.env && edit it && chmod 600 ${APP_DIR}/.env
  3. Create the Cloudflare Tunnel + set TUNNEL_TOKEN in .env
  4. As ${DEPLOY_USER}:  cd ${APP_DIR} && ./scripts/deploy.sh <tag>
EOF
