import asyncio
import os
import tempfile
from typing import Dict, Tuple
from app.language_manager import get_language_config
import psutil
from psutil import NoSuchProcess

def normalize_output(output: str) -> str:
    lines = output.splitlines()
    stripped_lines = [line.rstrip() for line in lines]
    while stripped_lines and stripped_lines[-1] == "":
        stripped_lines.pop()
    return "\n".join(stripped_lines)

async def run_command(
        cmd: str,
        stdin_input: str = "",
        timeout: float = 3.0,
        memory_limit: int=128
) -> Tuple[bool, bool,str, str, float,float]:
    start_time = asyncio.get_event_loop().time()
    peak_memory = 0.0
    is_mle = False
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )

        async def monitor_memory():
            nonlocal peak_memory, is_mle
            try:
                parent = psutil.Process(proc.pid)
            except NoSuchProcess:
                return
            while True:
                try:
                    if proc.returncode is not None:
                        break
                    total_rss = parent.memory_info().rss
                    for c in parent.children(recursive=True):
                        try:
                            total_rss += c.memory_info().rss
                        except psutil.NoSuchProcess:
                            continue
                    current_mem_mb = total_rss / (1024 * 1024)
                    if current_mem_mb > peak_memory:
                        peak_memory = current_mem_mb
                    if current_mem_mb > memory_limit:
                        is_mle = True
                        try:
                            for child in parent.children(recursive=True):
                                try:
                                    child.kill()
                                except psutil.NoSuchProcess:
                                    pass
                            parent.kill()
                        except psutil.NoSuchProcess:
                            pass
                        break
                    await asyncio.sleep(0.1)
                except NoSuchProcess:
                    break
        monitor_task = asyncio.create_task(monitor_memory())
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=stdin_input.encode("utf-8")),
            timeout=timeout
        )
        await monitor_task
        run_time = asyncio.get_event_loop().time() - start_time
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return False,is_mle, stdout, stderr, run_time,peak_memory
    except asyncio.TimeoutError:
        parent=psutil.Process(proc.pid)
        try:
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        await proc.wait()
        await monitor_task
        return True,False, "", "", timeout,peak_memory

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
    with tempfile.TemporaryDirectory() as tmp_dir:
        suffix = lang_config["file_suffix"]
        code_file = os.path.join(tmp_dir, f"main{suffix}")
        exe_file = os.path.join(tmp_dir, "main")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)
        compile_cmd = lang_config["compile_cmd"]
        if compile_cmd:
            real_compile_cmd = compile_cmd.format(src=code_file, exe=exe_file)
            timeout, is_mle, compile_out, compile_err, run_time,peak_memory = await run_command(real_compile_cmd, "", 10,memory_limit)
            if is_mle:
                return{
                    "status": "MLE",
                    "time": run_time,
                    "memory": peak_memory,
                    "info": "memory limit exceeded while compiling"
                }
            if timeout or compile_err.strip():
                return {
                    "status": "CE",
                    "time": 0,
                    "memory": 0,
                    "info": compile_err.strip()
                }
        run_cmd = lang_config["run_cmd"].format(file=code_file, exe=exe_file)
        is_timeout, is_mle, stdout, stderr, run_time, peak_mem = await run_command(
            run_cmd,
            stdin_input=input_data,
            timeout=time_limit,
            memory_limit=memory_limit
        )
        if is_timeout:
            return {"status": "TLE", "time": run_time, "memory": peak_mem, "info": "time limit exceeded"}
        if is_mle:
            return {"status": "MLE", "time": run_time, "memory": peak_mem, "info": "memory limit exceeded"}
        if stderr.strip():
            return {"status": "RE", "time": run_time, "memory": peak_mem, "info": stderr.strip()}
        normalized_stdout = normalize_output(stdout)
        normalized_expected = normalize_output(expected_output)
        if normalized_stdout == normalized_expected:
            return {"status": "AC", "time": run_time, "memory": peak_mem, "info": ""}
        else:
            return {"status": "WA", "time": run_time, "memory": peak_mem, "info": "wrong answer"}