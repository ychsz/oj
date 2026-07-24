#!/usr/bin/env bash
# Install Docker Engine inside WSL (Ubuntu 24.04) using the Aliyun mirror.
# Usage:  sudo bash scripts/install_docker_wsl.sh
#
# Why this exists: Adv3 requires ALL judging to run in the `oj-sandbox`
# Docker container. Docker is a system-level component (NOT a pip package),
# so it must be installed on the OS where `uvicorn` runs. On this machine
# `uvicorn` runs inside WSL, so Docker must be installed inside WSL too.
# (Docker Desktop on Windows can't be downloaded here — desktop.docker.com
# is unreachable from CN networks; the Aliyun apt mirror below is stable.)
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "[install_docker_wsl] must run as root (sudo). Try: sudo bash $0" >&2
    exit 1
fi

# keep apt non-interactive
export DEBIAN_FRONTEND=noninteractive

echo "[1/7] removing conflicting legacy packages ..."
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

echo "[2/7] installing apt prerequisites (incl. python3-venv so the WSL-side"
echo "      backend venv can be created later without another sudo) ..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release \
    python3-venv python3-pip

echo "[3/7] adding Aliyun docker-ce GPG key + apt source ..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
ARCH="$(dpkg --print-architecture)"
CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu ${CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list

echo "[4/7] apt-get update + installing docker-ce ..."
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

echo "[5/7] enabling + starting docker daemon (systemd) ..."
systemctl enable --now docker

echo "[6/7] adding current invoking user to the docker group ..."
# The user who invoked sudo (not root).
REAL_USER="${SUDO_USER:-$USER}"
if [[ -n "$REAL_USER" && "$REAL_USER" != "root" ]]; then
    usermod -aG docker "$REAL_USER"
    echo "  -> added '$REAL_USER' to group docker"
    echo "  -> NOTE: run 'wsl --shutdown' from Windows (or log out/in) for the group to take effect,"
    echo "           then docker will work WITHOUT sudo."
fi

echo "[7/7] configuring registry mirror for faster image pulls on CN networks ..."
mkdir -p /etc/docker
# NOTE: USTC/163 mirrors have shut down. These are the currently-working ones.
cat > /etc/docker/daemon.json <<'JSON'
{
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://docker.m.daocloud.io"
  ]
}
JSON
systemctl restart docker

echo "[8/8] building the oj-sandbox image (root is fine; image is shared) ..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
docker build -t oj-sandbox -f "$REPO_ROOT/Dockerfile" "$REPO_ROOT"
docker images oj-sandbox

echo
echo "[install_docker_wsl] DONE."
docker --version
echo
echo "Next steps:"
echo "  1. From Windows PowerShell:  wsl --shutdown   (then reopen WSL)"
echo "  2. In WSL:                    python3 -m venv .venv"
echo "  3. In WSL:                    .venv/bin/pip install -r requirements.txt"
echo "  4. In WSL:                    bash scripts/build_sandbox.sh"
echo "  5. In WSL:                    .venv/bin/uvicorn app.main:app --reload"
