#!/usr/bin/env bash
# Build (or rebuild) the oj-sandbox image used by the Docker judge.
# Usage: bash scripts/build_sandbox.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "[build_sandbox] docker not found on PATH. Install Docker first." >&2
    exit 1
fi

BASE_IMAGE="python:3.10-slim"

# Pre-fetch the base image. On CN networks docker.io is often unreachable
# and the registry-mirror configured in /etc/docker/daemon.json may be stale
# (several public mirrors e.g. USTC have shut down). Try a few known-good
# CN mirrors and retag to the canonical name so the Dockerfile's `FROM` line
# stays standard/portable. Users on networks that can reach docker.io
# directly are unaffected: the first `docker pull` succeeds and we skip.
if ! docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
    echo "[build_sandbox] pulling base image $BASE_IMAGE ..."
    if ! docker pull "$BASE_IMAGE"; then
        echo "[build_sandbox] docker.io unreachable; trying CN registry mirrors ..."
        pulled=0
        for m in docker.m.daocloud.io docker.1panel.live; do
            echo "[build_sandbox]   trying $m/library/$BASE_IMAGE"
            if docker pull "$m/library/$BASE_IMAGE"; then
                docker tag "$m/library/$BASE_IMAGE" "$BASE_IMAGE"
                pulled=1
                break
            fi
        done
        if [ "$pulled" -eq 0 ]; then
            echo "[build_sandbox] could not pull $BASE_IMAGE from any source." >&2
            echo "[build_sandbox] configure a working registry-mirror in /etc/docker/daemon.json" >&2
            echo "[build_sandbox] (e.g. {\"registry-mirrors\":[\"https://docker.1panel.live\"]}) and restart docker." >&2
            exit 1
        fi
    fi
fi

echo "[build_sandbox] building oj-sandbox from $ROOT/Dockerfile ..."
docker build -t oj-sandbox -f Dockerfile "$ROOT"
echo "[build_sandbox] done. Verify with: docker images oj-sandbox"
