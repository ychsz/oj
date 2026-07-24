from typing import Dict, Optional, List, Tuple
from app.security import validate_command

_supported_languages: Dict[str, Dict] = {}

def init_default_languages() -> None:
    _supported_languages.clear()
    _supported_languages["python"] = {
        "name": "Python 3.10",
        "compile_cmd": None,
        "run_cmd": "python {file}",
        "file_suffix": ".py",
        "default_time_limit": 3.0,
        "default_memory_limit": 128
    }
    _supported_languages["cpp"] = {
        "name": "GCC C++",
        "compile_cmd": "g++ -std=c++14 -O2 {src} -o {exe}",
        "run_cmd": "./{exe}",
        "file_suffix": ".cpp",
        "default_time_limit": 1.0,
        "default_memory_limit": 128
    }
    for lang_id, cfg in _supported_languages.items():
        if cfg["compile_cmd"]:
            ok, reason = validate_command(cfg["compile_cmd"], "compile")
            if not ok:
                raise RuntimeError(f"built-in {lang_id} compile_cmd invalid: {reason}")
        ok, reason = validate_command(cfg["run_cmd"], "run")
        if not ok:
            raise RuntimeError(f"built-in {lang_id} run_cmd invalid: {reason}")

def reset_languages() -> None:
    init_default_languages()

def get_all_languages() -> Dict[str, List]:
    result: Dict[str, List] = {
        "id": [],
        "name": [],
        "default_time_limit": [],
        "default_memory_limit": []
    }
    for lang_id, config in _supported_languages.items():
        result["id"].append(lang_id)
        result["name"].append(config["name"])
        result["default_time_limit"].append(config["default_time_limit"])
        result["default_memory_limit"].append(config["default_memory_limit"])
    return result

def get_language_config(lang_id: str) -> Optional[Dict]:
    return _supported_languages.get(lang_id)

def register_language(
        lang_id: str,
        name: str,
        compile_cmd: Optional[str],
        run_cmd: str,
        file_suffix: str,
        default_time_limit: float = 3.0,
        default_memory_limit: int = 128
) -> Tuple[bool, str]:
    if lang_id in _supported_languages:
        return False, "language already exists"
    if not run_cmd or not run_cmd.strip():
        return False, "run_cmd is required"
    if not file_suffix or not file_suffix.strip().startswith("."):
        return False, "file_suffix must start with '.'"
    if compile_cmd:
        ok, reason = validate_command(compile_cmd, "compile")
        if not ok:
            return False, f"compile_cmd rejected: {reason}"
    ok, reason = validate_command(run_cmd, "run")
    if not ok:
        return False, f"run_cmd rejected: {reason}"

    _supported_languages[lang_id] = {
        "name": name,
        "compile_cmd": compile_cmd,
        "run_cmd": run_cmd,
        "file_suffix": file_suffix,
        "default_time_limit": default_time_limit,
        "default_memory_limit": default_memory_limit
    }
    return True, ""

init_default_languages()