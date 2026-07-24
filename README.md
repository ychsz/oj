# oj

Small-scale Online Judge built with FastAPI, coursework for THU *"Programming Training"*.

Backend (`app/`) exposes a JSON API under `/api/`. An optional Streamlit frontend
lives in `frontend/` and talks to the backend over HTTP.

## Prerequisites

This project has TWO kinds of dependencies:

### 1. Python packages (`pip install -r requirements.txt`)
`fastapi`, `uvicorn`, `bcrypt`, `itsdangerous` for the backend; `streamlit`,
`requests` for the optional frontend. Standard `pip` install.

### 2. Docker (system-level, **mandatory for judging** — Adv3)

> Docker is **not** a Python package and **cannot** be installed via
> `pip` / `requirements.txt`. It is a standalone system component (daemon +
> CLI) that must be installed on the OS where `uvicorn` runs.

**Why:** Per Adv3 (安全机制), every submission is judged *inside* a
locked-down Docker container (`oj-sandbox` image). There is **no host-side
fallback** — if Docker or the image is missing, every submission returns
status `SE` (sandbox error) with the message
`docker executable 'docker' not found on PATH; ...`.

**The `docker` CLI must be reachable from the same environment that runs
`uvicorn`** (the judge calls `docker run` via `subprocess`). So:
- if you run `uvicorn` on Windows → install Docker Desktop on Windows;
- if you run `uvicorn` inside WSL → install Docker Engine inside that WSL distro.

#### Install Docker

**WSL (Ubuntu) — recommended if you run the backend in WSL:**
```bash
sudo bash scripts/install_docker_wsl.sh   # adds Aliyun mirror, installs docker-ce, starts daemon
# then from Windows PowerShell:
wsl --shutdown                              # so the `docker` group membership takes effect
```
(Why a script: `desktop.docker.com` is often unreachable from CN networks;
the Aliyun apt mirror in this script is stable. The script also installs
`python3-venv`/`python3-pip` so the backend venv can be created later.)

**Windows (Docker Desktop) — only if you run the backend on Windows:**
Download & install Docker Desktop from https://www.docker.com/products/docker-desktop
(requires WSL2 backend; enable WSL2 integration for your distro). After install,
`docker` is available in both PowerShell and WSL.

Verify:
```bash
docker version          # daemon responds
docker images oj-sandbox
```

#### Build the sandbox image (once, after Docker is installed)
```bash
bash scripts/build_sandbox.sh              # docker build -t oj-sandbox -f Dockerfile .
```
Health-check from the running backend: `GET /api/sandbox/status` →
`{docker_available, image_present, image}`.

## Run

From the repo root (data dirs `users/`, `problems/`, `submissions/` are
referenced by relative path — **must run from repo root**):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```
Default admin: username `admin`, password `admintestpassword`.

Frontend (optional, separate process, can run anywhere that reaches the backend):
```bash
streamlit run frontend/app.py
```

## Sandbox & security (Adv3)

All judging goes through `app/docker_sandbox.run_in_sandbox`, which runs each
compile/run step as `docker run --rm -i --network=none --read-only
--tmpfs /tmp --memory/--memory-swap/--cpus --cap-drop=ALL
--security-opt no-new-privileges --pids-limit=64 --user 1000:1000 -v <tmp>:/sandbox -w /sandbox`.
No seccomp/cgroups/resource modules are used directly — every isolation &
limit is a Docker flag.

Language commands registered via `POST /api/languages/` are validated by
`app/security.validate_command` (whitelist of leading programs + blacklist of
shell meta-characters / dangerous binaries / path escapes); the rendered
command is re-validated at judge time.

Submission status codes: `AC` / `WA` / `TLE` / `MLE` / `RE` / `CE` / `UKE` /
`SE` (sandbox error — Docker/image missing).
