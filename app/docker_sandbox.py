import asyncio
import os
import shlex
import shutil
import subprocess
from typing import List, Tuple
SANDBOX_IMAGE = "oj-sandbox"
DOCKER_BIN = os.environ.get("DOCKER_BIN", "docker")

class SandboxError(Exception):
    pass

def docker_available() -> bool:
    if shutil.which(DOCKER_BIN) is None:
        return False
    try:
        proc = subprocess.run(
            [DOCKER_BIN, "version", "--format", "{{.Server.Version}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False

def sandbox_image_present() -> bool:
    if shutil.which(DOCKER_BIN) is None:
        return False
    try:
        proc = subprocess.run(
            [DOCKER_BIN, "image", "inspect", SANDBOX_IMAGE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False

async def ensure_sandbox_ready() -> None:
    if shutil.which(DOCKER_BIN) is None:
        raise SandboxError(
            f"docker executable {DOCKER_BIN!r} not found on PATH; "
            "install Docker and run scripts/build_sandbox.sh"
        )
    proc = await asyncio.create_subprocess_exec(
        DOCKER_BIN, "version", "--format", "{{.Server.Version}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise SandboxError(
            "docker daemon not reachable: "
            + (err.decode("utf-8", "replace").strip() or "unknown error")
        )
    proc = await asyncio.create_subprocess_exec(
        DOCKER_BIN, "image", "inspect", SANDBOX_IMAGE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise SandboxError(
            f"image {SANDBOX_IMAGE!r} not found; "
            f"run: bash scripts/build_sandbox.sh  ({err.decode('utf-8','replace').strip()})"
        )

def _build_docker_argv(
        host_tmpdir: str,
        cmd_argv: List[str],
        timeout: float,
        memory_limit_mb: int,
        cpus: float = 1.0,
) -> List[str]:
    mem = max(int(memory_limit_mb), 4)
    inner_timeout = max(timeout, 1)
    timeout_argv = ["timeout", "-s", "KILL", f"{inner_timeout}"]
    full_cmd = timeout_argv + cmd_argv
    return [
        DOCKER_BIN, "run", "--rm",
        "-i",
        "--network=none",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=64m,mode=1777",
        f"--memory={mem}m",
        f"--memory-swap={mem}m",
        f"--cpus={cpus}",
        "--cap-drop=ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit=64",
        "--user", "1000:1000",
        "-v", f"{host_tmpdir}:/sandbox:rw",
        "-w", "/sandbox",
        SANDBOX_IMAGE,
        *full_cmd,
    ]

async def run_in_sandbox(
        cmd: str,
        workdir: str,
        stdin_input: str = "",
        timeout: float = 3.0,
        memory_limit_mb: int = 128,
        cpus: float = 1.0,
) -> Tuple[bool, bool, int, str, str, float, float]:
    await ensure_sandbox_ready()
    cmd_argv = shlex.split(cmd, posix=True)
    if not cmd_argv:
        raise SandboxError("empty command after tokenize")
    if not os.path.isdir(workdir):
        raise SandboxError(f"workdir does not exist: {workdir}")
    host_tmpdir = os.path.abspath(workdir)
    docker_argv = _build_docker_argv(
        host_tmpdir=host_tmpdir,
        cmd_argv=cmd_argv,
        timeout=timeout,
        memory_limit_mb=memory_limit_mb,
        cpus=cpus,
    )
    start = asyncio.get_event_loop().time()
    proc = await asyncio.create_subprocess_exec(
        *docker_argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    outer_deadline = timeout + 3.0
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(input=stdin_input.encode("utf-8", "ignore")),
            timeout=outer_deadline,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        try:
            await proc.wait()
        except Exception:
            pass
        run_time = asyncio.get_event_loop().time() - start
        return True, False, 124, "", "outer timeout (docker hung)", run_time, 0.0
    run_time = asyncio.get_event_loop().time() - start
    rc = proc.returncode if proc.returncode is not None else -1
    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    is_timeout = rc == 124
    if is_timeout:
        return True, False, rc, stdout, stderr, run_time, 0.0
    is_mle = rc == 137
    peak_mem = float(memory_limit_mb) if is_mle else 0.0
    return False, is_mle, rc, stdout, stderr, run_time, peak_mem

def init_sandbox() -> None:
    try:
        if shutil.which(DOCKER_BIN) is None:
            return
    except Exception:
        pass
