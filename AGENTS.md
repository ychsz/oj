# AGENTS.md

Compact guidance for OpenCode sessions working in this repo. A small FastAPI-based
Online Judge (THU "Programming Training" coursework).

## Run

- Entry point is `app/main.py` (`app = FastAPI(...)`). Start from the **repo root**:
  `uvicorn app.main:app --reload`
- Repo root is mandatory: data dirs are referenced by **relative path** in every
  manager (`USER_DIR = "users"`, `PROBLEM_DIR = "problems"`, `SUBMISSION_DIR = "submissions"`).
  Running elsewhere silently creates empty data dirs.
- Install deps: `pip install -r requirements.txt` (fastapi, uvicorn, bcrypt; streamlit/requests are for the frontend).
- To judge C++ submissions, `g++` must be on PATH (compile cmd `g++ -std=c++14 -O2 ...`).
- To judge Python submissions, a `python` executable must be on PATH — the run cmd is
  `python {file}`, **not** `python3`. On systems with only `python3` (e.g. fresh WSL/Debian),
  Python submissions fail to run; add a `python` symlink/alias before testing submissions.
- Default admin is auto-seeded on startup: username `admin`, password `admintestpassword`.
- **Docker sandbox (Adv3)**: ALL judging runs inside the `oj-sandbox` Docker image.
  Build it once with `bash scripts/build_sandbox.sh` (runs `docker build -t oj-sandbox -f
  Dockerfile .`). The `docker` CLI + a running daemon are required. If Docker or the image
  is missing at judge time, the submission is marked `SE` (sandbox error) — there is **no**
  host-side fallback. Check status via `GET /api/sandbox/status`. Resource limits
  (`--memory`, `--memory-swap`, `--cpus`) and isolation (`--network=none`, `--read-only`,
  `--cap-drop=ALL`, `--security-opt no-new-privileges`, `--pids-limit`, non-root uid 1000)
  are all expressed as Docker flags — no direct seccomp/cgroups/resource modules are used.

## State & persistence

- `user_manager`, `submission_manager`, `problem_manager` each keep an in-memory dict
  loaded from JSON files at **import time**, and write through to disk on every mutation.
  Restart reloads users/submissions/problems from `*.json`.
- `audit_manager._audit_logs` is **in-memory only** (no save-to-file). Audit logs are
  lost on restart; do not rely on them surviving a reload.
- `users/`, `submissions/`, and `problems/` contain **committed** sample data (e.g. the
  seeded admin user, sample submissions). `.gitignore` only excludes `.idea/` and
  `__pycache__/` — don't blindly delete these dirs. To wipe at runtime, use the
  `POST /api/reset/` admin endpoint (also clears the current session).
- Export/import round-trips via `GET /api/export/` and `POST /api/import/` (JSON upload).
  Note export field naming differs from internal storage (e.g. `submission_id` vs `id`,
  `password` vs `password_hash`, `counts` vs `total_score`, `details` vs `testcases`).

## Tooling & conventions

- **No** test suite, linter, type checker, or formatter is configured. Don't assume
  `pytest`/`ruff`/`mypy` exist; verify any new tooling before adding commands.
- Imports use the `app.` package prefix (e.g. `from app.judge import ...`), so the repo
  root must be on `sys.path` — running modules directly as scripts will break.
- Commit style: `type(stepN): summary` (e.g. `feat(step4): ...`, `fix(step2): ...`,
  `refactor(persistence): ...`). Work is staged in numbered steps; match the style.

## Architecture notes

- All HTTP routes live in `app/main.py` under `/api/`. Auth is session-based via
  `SessionMiddleware` (secret key is hardcoded — fine for coursework, not production).
  Every protected route calls `get_current_user(request)` then checks `role` (`user` /
  `admin` / `banned`).
- Managers are module-level singletons; their init code runs on import (e.g.
  `init_default_admin()` and `init_default_languages()`). Importing a manager has side
  effects — don't import them in tests/utils casually.
- `judge.py` runs **untrusted user code** inside the `oj-sandbox` Docker container
  via `app/docker_sandbox.run_in_sandbox` (argv list, `shell=False`). There is **no**
  host-side process execution of submissions anymore — Docker is the only sandbox.
  No seccomp/cgroups/resource modules are used directly; all isolation & limits are
  Docker flags. If Docker/image is missing, judge returns `SE` (sandbox error).
- Command templates registered via `POST /api/languages/` are security-validated by
  `app/security.validate_command` (whitelist of leading programs + blacklist of shell
  meta-characters, dangerous binaries, path escapes) before being stored; the rendered
  command is re-validated at judge time as defense-in-depth.
- Submission judging is fire-and-forget: `create_submission` schedules
  `run_judge_task` via `asyncio.create_task`, so the result is polled later through
  `GET /api/submissions/{id}`. `rejudge` resets and reschedules the same way.
