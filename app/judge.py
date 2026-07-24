import os
import tempfile
from typing import Dict, Optional, Tuple
from app.language_manager import get_language_config
from app.docker_sandbox import run_in_sandbox, SandboxError
from app.security import validate_command, validate_rendered_command

def normalize_output(output: str) -> str:
    lines = output.splitlines()
    stripped_lines = [line.rstrip() for line in lines]
    while stripped_lines and stripped_lines[-1] == "":
        stripped_lines.pop()
    return "\n".join(stripped_lines)

def compare_standard(actual: str, expected: str) -> bool:
    return normalize_output(actual) == normalize_output(expected)

def compare_strict(actual: str, expected: str) -> bool:
    return actual == expected

async def run_spj_judge(
        spj_script_path: str,
        input_data: str,
        actual_output: str,
        expected_output: str,
        time_limit: float,
        memory_limit: int,
) -> Tuple[str, str]:
    if not spj_script_path or not os.path.exists(spj_script_path):
        return "SE", "no SPJ script configured"
    spj_basename = "spj.py"
    input_basename = "input.txt"
    output_basename = "output.txt"
    answer_basename = "answer.txt"
    spj_cmd = f"python {spj_basename} {input_basename} {output_basename} {answer_basename}"
    ok, reason = validate_rendered_command(spj_cmd)
    if not ok:
        return "SE", f"spj command rejected: {reason}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        _chmod_for_container(tmp_dir, is_dir=True)
        dst_spj = os.path.join(tmp_dir, spj_basename)
        with open(dst_spj, "w", encoding="utf-8") as f:
            with open(spj_script_path, "r", encoding="utf-8") as src:
                f.write(src.read())
        _chmod_for_container(dst_spj, is_dir=False)
        for name, data in (
            (input_basename, input_data),
            (output_basename, actual_output),
            (answer_basename, expected_output),
        ):
            p = os.path.join(tmp_dir, name)
            with open(p, "w", encoding="utf-8") as f:
                f.write(data)
            _chmod_for_container(p, is_dir=False)
        try:
            is_timeout, is_mle, stdout, stderr, run_time, peak_mem = await _sandbox_run(
                cmd=spj_cmd,
                workdir=tmp_dir,
                stdin_input="",
                timeout=max(time_limit, 1.0),
                memory_limit=max(memory_limit, 64),
            )
        except SandboxError as e:
            return "SE", str(e)
        if is_timeout:
            return "SE", "SPJ time limit exceeded"
        if is_mle:
            return "SE", "SPJ memory limit exceeded"
        if stderr.strip():
            return "SE", f"SPJ error: {stderr.strip()}"
        return "AC" if stdout.strip() in ("0", "") else "WA", stdout.strip() or "0"

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
        memory_limit: int,
        judge_mode: str = "standard",
        spj_script_path: Optional[str] = None
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
        if judge_mode == "strict":
            if compare_strict(stdout, expected_output):
                return {"status": "AC", "time": run_time, "memory": peak_mem, "info": ""}
            return {"status": "WA", "time": run_time, "memory": peak_mem,
                    "info": "wrong answer (strict)"}
        if judge_mode == "spj":
            status, info = await run_spj_judge(
                spj_script_path=spj_script_path or "",
                input_data=input_data,
                actual_output=stdout,
                expected_output=expected_output,
                time_limit=time_limit,
                memory_limit=memory_limit,
            )
            if status == "AC":
                return {"status": "AC", "time": run_time, "memory": peak_mem, "info": ""}
            if status == "WA":
                return {"status": "WA", "time": run_time, "memory": peak_mem, "info": info}
            return {"status": status, "time": run_time, "memory": peak_mem, "info": info}
        if compare_standard(stdout, expected_output):
            return {"status": "AC", "time": run_time, "memory": peak_mem, "info": ""}
        return {"status": "WA", "time": run_time, "memory": peak_mem,
                "info": "wrong answer"}