import json
import os
from typing import List, Dict, Optional, Tuple
PROBLEM_DIR = "problems"
SPJ_DIR = "spj"

VALID_JUDGE_MODES = {"standard", "strict", "spj"}

def get_problem_file_path(problem_id: str) -> str:
    return os.path.join(PROBLEM_DIR, f"{problem_id}.json")

def get_spj_script_path(problem_id: str) -> str:
    return os.path.join(SPJ_DIR, f"{problem_id}.py")

def init_spj_dir() -> None:
    if not os.path.exists(SPJ_DIR):
        os.makedirs(SPJ_DIR)

def has_spj_script(problem_id: str) -> bool:
    return os.path.exists(get_spj_script_path(problem_id))

def save_spj_script(problem_id: str, content: str) -> None:
    init_spj_dir()
    file_path = get_spj_script_path(problem_id)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def delete_spj_script(problem_id: str) -> bool:
    file_path = get_spj_script_path(problem_id)
    if not os.path.exists(file_path):
        return False
    os.remove(file_path)
    return True

def get_spj_script_info(problem_id: str) -> Optional[Dict]:
    file_path = get_spj_script_path(problem_id)
    if not os.path.exists(file_path):
        return None
    return {
        "problem_id": problem_id,
        "filename": os.path.basename(file_path),
        "size": os.path.getsize(file_path)
    }

def load_problem(problem_id: str) -> Optional[Dict]:
    file_path = get_problem_file_path(problem_id)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        problem = json.load(f)
    return problem

def get_problem_list() -> List[Dict]:
    problem_list = []
    for filename in os.listdir(PROBLEM_DIR):
        problem_id = filename[:-5]
        problem = load_problem(problem_id)
        if problem:
            problem_list.append({
                "id": problem["id"],
                "title": problem["title"]
            })
    return problem_list

def validate_and_fill_problem(problem_data: Dict) -> Tuple[bool, str, Dict]:
    required_fields = [
        "id", "title", "description",
        "input_description", "output_description",
        "samples", "constraints", "testcases"
    ]
    for field in required_fields:
        if field not in problem_data:
            return False, f"missing required field: {field}", {}
    default_str_fields = ["hint", "source", "author", "difficulty"]
    for field in default_str_fields:
        if field not in problem_data:
            problem_data[field] = ""
    if "tags" not in problem_data:
        problem_data["tags"] = []
    if "time_limit" not in problem_data:
        problem_data["time_limit"] = 3.0
    else:
        problem_data["time_limit"] = float(problem_data["time_limit"])
    if "memory_limit" not in problem_data:
        problem_data["memory_limit"] = 128
    else:
        problem_data["memory_limit"] = int(problem_data["memory_limit"])
    if "public_cases" not in problem_data:
        problem_data["public_cases"] = False
    else:
        problem_data["public_cases"] = bool(problem_data["public_cases"])
    if "judge_mode" not in problem_data or not problem_data["judge_mode"]:
        problem_data["judge_mode"] = "standard"
    else:
        mode = str(problem_data["judge_mode"])
        if mode not in VALID_JUDGE_MODES:
            return False, f"invalid judge_mode: {mode!r} (allowed: {sorted(VALID_JUDGE_MODES)})", {}
        problem_data["judge_mode"] = mode
    return True, "valid", problem_data

def add_problem(problem_data: Dict) -> Tuple[bool, str, str]:
    valid, msg, filled_problem = validate_and_fill_problem(problem_data)
    if not valid:
        return False, msg, ""
    problem_id = filled_problem["id"]
    if load_problem(problem_id) is not None:
        return False, "problem id already exists", problem_id
    file_path = get_problem_file_path(problem_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(filled_problem, f, ensure_ascii=False, indent=2)
    return True, "add success", problem_id

def delete_problem(problem_id: str) -> bool:
    file_path = get_problem_file_path(problem_id)
    if not os.path.exists(file_path):
        return False
    os.remove(file_path)
    return True

def update_problem_log_visibility(problem_id: str, public_cases: bool) -> Tuple[bool, str]:
    problem = load_problem(problem_id)
    if not problem:
        return False, "problem not found"
    problem["public_cases"] = public_cases
    file_path = get_problem_file_path(problem_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(problem, f, ensure_ascii=False, indent=2)
    return True, "log visibility updated"

def update_problem_judge_mode(problem_id: str, judge_mode: str) -> Tuple[bool, str]:
    problem = load_problem(problem_id)
    if not problem:
        return False, "problem not found"
    if judge_mode not in VALID_JUDGE_MODES:
        return False, f"invalid judge_mode: {judge_mode!r} (allowed: {sorted(VALID_JUDGE_MODES)})"
    problem["judge_mode"] = judge_mode
    file_path = get_problem_file_path(problem_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(problem, f, ensure_ascii=False, indent=2)
    return True, "judge mode updated"

def reset_problems() -> None:
    for filename in os.listdir(PROBLEM_DIR):
        if filename.endswith(".json"):
            os.remove(os.path.join(PROBLEM_DIR, filename))
    if os.path.isdir(SPJ_DIR):
        for filename in os.listdir(SPJ_DIR):
            if filename.endswith(".py"):
                os.remove(os.path.join(SPJ_DIR, filename))

def export_problems() -> List[Dict]:
    problems = []
    for filename in os.listdir(PROBLEM_DIR):
        if filename.endswith(".json"):
            problem_id = filename[:-5]
            problem = load_problem(problem_id)
            if problem:
                problems.append(problem)
    return problems

def import_problems(problems_data: List[Dict]) -> None:
    for problem in problems_data:
        problem_id = problem["id"]
        file_path = get_problem_file_path(problem_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(problem, f, ensure_ascii=False, indent=2)

init_spj_dir()