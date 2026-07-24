import os
import tempfile
from typing import Dict, Tuple
from app.language_manager import get_language_config
from app.docker_sandbox import run_in_sandbox, SandboxError
from app.security import validate_command, validate_rendered_command

def normalize_output(output: str) -> str:
    lines = output.splitlines()
    stripped_lines = [line.rstrip() for line in lines]
    while stripped_lines and stripped_lines[-1] == "":
        stripped_lines.pop()
    return "\n".join(stripped_lines)

def _chmod_for_container(path: str, is_dir: bool = False) -> None:
    mode = 0o777 if is_dir else 0o666
    try:
        os.chmod(path, mode)
    except OSError:
        pass

async def _sandbox_run(
        cmd: str,
        workdir: str,
        stdin_input: str,
        timeout: float,
        memory_limit: int,
) -> Tuple[bool, bool, str, str, float, float]:
    ok, reason = validate_rendered_command(cmd)
    if not ok:
        raise SandboxError(f"rendered command rejected: {reason}")
    is_timeout, is_mle, rc, stdout, stderr, run_time, peak_mem = await run_in_sandbox(
        cmd=cmd,
        workdir=workdir,
        stdin_input=stdin_input,
        timeout=timeout,
        memory_limit_mb=memory_limit,
    )
    return is_timeout, is_mle, stdout, stderr, run_time, peak_mem

async def judge_single_testcase(
        code: str,
        language: str,
        input_data: str,
        expected_output: str,
        time_limit: float,
        memory_limit: int
) -> Dict:
    lang_config = get_language_config(language)
    if not lang_config:
        return {"status": "UKE", "time": 0, "memory": 0, "info": "language not supported"}
    compile_cmd_template = lang_config.get("compile_cmd")
    if compile_cmd_template:
        ok, reason = validate_command(compile_cmd_template, "compile")
        if not ok:
            return {"status": "UKE", "time": 0, "memory": 0,
                    "info": f"invalid compile command: {reason}"}
    run_cmd_template = lang_config.get("run_cmd", "")
    ok, reason = validate_command(run_cmd_template, "run")
    if not ok:
        return {"status": "UKE", "time": 0, "memory": 0,
                "info": f"invalid run command: {reason}"}
    with tempfile.TemporaryDirectory() as tmp_dir:
        _chmod_for_container(tmp_dir, is_dir=True)
        suffix = lang_config["file_suffix"]
        src_basename = f"main{suffix}"
        exe_basename = "main"
        code_file = os.path.join(tmp_dir, src_basename)
        exe_file = os.path.join(tmp_dir, exe_basename)
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)
        _chmod_for_container(code_file, is_dir=False)
        if compile_cmd_template:
            rendered_compile = compile_cmd_template.format(
                src=src_basename, exe=exe_basename
            )
            try:
                c_timeout, c_mle, c_out, c_err, c_time, c_peak = await _sandbox_run(
                    cmd=rendered_compile,
                    workdir=tmp_dir,
                    stdin_input="",
                    timeout=10.0,
                    memory_limit=max(memory_limit, 256),
                )
            except SandboxError as e:
                return {"status": "SE", "time": 0, "memory": 0, "info": str(e)}
            if c_timeout:
                return {"status": "CE", "time": c_time, "memory": c_peak,
                        "info": "compilation time limit exceeded"}
            if c_mle:
                return {"status": "MLE", "time": c_time, "memory": c_peak,
                        "info": "memory limit exceeded while compiling"}
            if c_err.strip():
                return {"status": "CE", "time": 0, "memory": 0,
                        "info": c_err.strip()}
        run_cmd = run_cmd_template.format(file=src_basename, exe=exe_basename)
        try:
            is_timeout, is_mle, stdout, stderr, run_time, peak_mem = await _sandbox_run(
                cmd=run_cmd,
                workdir=tmp_dir,
                stdin_input=input_data,
                timeout=time_limit,
                memory_limit=memory_limit,
            )
        except SandboxError as e:
            return {"status": "SE", "time": 0, "memory": 0, "info": str(e)}
        if is_timeout:
            return {"status": "TLE", "time": run_time, "memory": peak_mem,
                    "info": "time limit exceeded"}
        if is_mle:
            return {"status": "MLE", "time": run_time, "memory": peak_mem,
                    "info": "memory limit exceeded"}
        if stderr.strip():
            return {"status": "RE", "time": run_time, "memory": peak_mem,
                    "info": stderr.strip()}
        normalized_stdout = normalize_output(stdout)
        normalized_expected = normalize_output(expected_output)
        if normalized_stdout == normalized_expected:
            return {"status": "AC", "time": run_time, "memory": peak_mem, "info": ""}
        return {"status": "WA", "time": run_time, "memory": peak_mem,
                "info": "wrong answer"}