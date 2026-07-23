import sys
from typing import Dict, Optional, List

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
        "run_cmd": "{exe}" if sys.platform=="win32" else "./{exe}",
        "file_suffix": ".cpp",
        "default_time_limit": 1.0,
        "default_memory_limit": 128
    }

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
) -> bool:
    if lang_id in _supported_languages:
        return False

    _supported_languages[lang_id] = {
        "name": name,
        "compile_cmd": compile_cmd,
        "run_cmd": run_cmd,
        "file_suffix": file_suffix,
        "default_time_limit": default_time_limit,
        "default_memory_limit": default_memory_limit
    }
    return True

init_default_languages()