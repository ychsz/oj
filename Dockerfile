# OJ sandbox image for Adv3 (Docker-based judging).
#
# This image is intentionally minimal: only the runtime + compiler toolchain
# needed to judge Python and C++ submissions. It is run with a locked-down
# `docker run` flag set (see app/docker_sandbox.py): --network=none,
# --read-only, --cap-drop=ALL, --security-opt no-new-privileges, --pids-limit,
# --memory/--memory-swap/--cpus. All isolation & resource limits therefore
# come from Docker.

FROM python:3.10-slim

# Compiler toolchain for C/C++; keep image small (no recommended/doc stacks).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Dedicated non-root judge user (uid 1000, gid 1000). The host mounts the
# per-submission tmp dir at /sandbox with mode 0o777 and source files 0o666,
# so this user can read/write the submitted code and produced binaries.
RUN groupadd -g 1000 oj \
    && useradd -m -u 1000 -g 1000 -s /usr/sbin/nologin oj

WORKDIR /sandbox

USER oj

# Sanity: confirm python + g++ are reachable. Fails the build early otherwise.
RUN python --version && g++ --version
