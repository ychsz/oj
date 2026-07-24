import uuid
import asyncio
import os
import json
from typing import Dict, Optional,List,Tuple
from app.problem_manager import load_problem, get_spj_script_path, has_spj_script
from app.judge import judge_single_testcase
from app.language_manager import get_language_config
from app.user_manager import increment_resolve_count

SUBMISSION_DIR = "submissions"

def init_submission_dir() -> None:
    if not os.path.exists(SUBMISSION_DIR):
        os.makedirs(SUBMISSION_DIR)

def get_submission_file_path(submission_id: str) -> str:
    return os.path.join(SUBMISSION_DIR, f"{submission_id}.json")

def save_submission_to_file(submission: Dict) -> None:
    file_path = get_submission_file_path(submission["id"])
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(submission, f, ensure_ascii=False, indent=2)

def load_submission_from_file(submission_id: str) -> Optional[Dict]:
    file_path = get_submission_file_path(submission_id)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_all_submissions() -> Dict[str, Dict]:
    submissions = {}
    for filename in os.listdir(SUBMISSION_DIR):
        if filename.endswith(".json"):
            sub_id = filename[:-5]
            sub = load_submission_from_file(sub_id)
            if sub:
                submissions[sub_id] = sub
    return submissions

def create_submission(problem_id: str, language: str, code: str,user_id:str="anonymous") -> str:
    submission_id = uuid.uuid4().hex
    submission = {
        "id": submission_id,
        "problem_id": problem_id,
        "language": language,
        "code": code,
        "user_id":user_id,
        "status": "pending",
        "score": 0,
        "total_score": 0,
        "testcases": [],
        "info":""
    }
    _submissions[submission_id] = submission
    save_submission_to_file(submission)
    asyncio.create_task(run_judge_task(submission_id))
    return submission_id

def get_submission(submission_id: str) -> Optional[Dict]:
    return _submissions.get(submission_id)

def get_submission_list(
        user_id: Optional[str] = None,
        problem_id: Optional[str] = None,
        status: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
) -> Tuple[int, List[Dict]]:
    all_submissions = list(_submissions.values())
    filtered = []
    for sub in all_submissions:
        if user_id is not None and sub["user_id"] != user_id:
            continue
        if problem_id is not None and sub["problem_id"] != problem_id:
            continue
        if status is not None and sub["status"] != status:
            continue
        filtered.append(sub)
    total_count = len(filtered)
    if page is None and page_size is None:
        return total_count, filtered
    if page is None:
        page = 1
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_submissions = filtered[start_index:end_index]
    return total_count, paginated_submissions

async def rejudge_submission(submission_id: str) -> Optional[bool]:
    submission = _submissions.get(submission_id)
    if not submission:
        return None
    submission["status"] = "pending"
    submission["score"] = 0
    submission["total_score"] = 0
    submission["testcases"] = []
    save_submission_to_file(submission)
    asyncio.create_task(run_judge_task(submission_id))
    return True

async def run_judge_task(submission_id: str) -> None:
    submission = _submissions.get(submission_id)
    if not submission:
        return
    try:
        problem = load_problem(submission["problem_id"])
        if not problem:
            submission["status"] = "error"
            submission["info"]="problem not found"
            save_submission_to_file(submission)
            return
        lang_config = get_language_config(submission["language"])
        default_time = lang_config["default_time_limit"]
        default_memory = lang_config["default_memory_limit"]
        time_limit = problem.get("time_limit", default_time)
        memory_limit = problem.get("memory_limit", default_memory)
        testcases = problem.get("testcases", [])
        total_score = len(testcases) * 10
        submission["total_score"] = total_score
        passed_count = 0
        judge_mode = problem.get("judge_mode", "standard")
        spj_script_path = None
        if judge_mode == "spj":
            if has_spj_script(submission["problem_id"]):
                spj_script_path = get_spj_script_path(submission["problem_id"])
            else:
                submission["status"] = "error"
                submission["info"] = "judge_mode is spj but no SPJ script uploaded"
                save_submission_to_file(submission)
                return
        for tc in testcases:
            result = await judge_single_testcase(
                code=submission["code"],
                language=submission["language"],
                input_data=tc["input"],
                expected_output=tc["output"],
                time_limit=time_limit,
                memory_limit=memory_limit,
                judge_mode=judge_mode,
                spj_script_path=spj_script_path
            )
            submission["testcases"].append(result)
            if result["status"] == "AC":
                passed_count += 1
        submission["score"] = passed_count * 10
        submission["status"] = "success"
        if submission["score"] == submission["total_score"]:
            increment_resolve_count(submission["user_id"], submission["problem_id"])
        save_submission_to_file(submission)
    except Exception as e:
        submission["status"] = "error"
        submission["info"] = str(e)
        save_submission_to_file(submission)

def reset_submissions() -> None:
    global _submissions
    for filename in os.listdir(SUBMISSION_DIR):
        if filename.endswith(".json"):
            os.remove(os.path.join(SUBMISSION_DIR, filename))
    _submissions.clear()

def export_submissions() -> List[Dict]:
    result = []
    for sub in _submissions.values():
        details = []
        for idx, tc in enumerate(sub["testcases"], start=1):
            details.append({
                "id": idx,
                "result": tc["status"],
                "time": tc["time"],
                "memory": tc["memory"]
            })
        result.append({
            "submission_id": sub["id"],
            "user_id": sub["user_id"],
            "problem_id": sub["problem_id"],
            "language": sub["language"],
            "code": sub["code"],
            "status": sub["status"],
            "details": details,
            "score": sub["score"],
            "counts": sub["total_score"]
        })
    return result

def import_submissions(submissions_data: List[Dict]) -> None:
    global _submissions
    for sub_data in submissions_data:
        sub_id = sub_data["submission_id"]
        testcases = []
        for detail in sub_data.get("details", []):
            testcases.append({
                "status": detail["result"],
                "time": detail["time"],
                "memory": detail["memory"],
                "info": ""
            })
        submission = {
            "id": sub_id,
            "user_id": sub_data["user_id"],
            "problem_id": sub_data["problem_id"],
            "language": sub_data["language"],
            "code": sub_data["code"],
            "status": sub_data["status"],
            "score": sub_data["score"],
            "total_score": sub_data["counts"],
            "testcases": testcases
        }
        _submissions[sub_id] = submission
        save_submission_to_file(submission)

init_submission_dir()
_submissions = load_all_submissions()