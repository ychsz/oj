import json
import os
from typing import List, Dict, Optional, Tuple
PROBLEM_DIR = "problems"

def get_problem_file_path(problem_id: str) -> str:
    return os.path.join(PROBLEM_DIR, f"{problem_id}.json")

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