import uuid
import asyncio
from typing import Dict, Optional
from app.problem_manager import load_problem
from app.judge import judge_single_testcase
from app.language_manager import get_language_config

_submissions: Dict[str, Dict] = {}

def create_submission(problem_id: str, language: str, code: str) -> str:
    submission_id = uuid.uuid4().hex
    _submissions[submission_id] = {
        "id": submission_id,
        "problem_id": problem_id,
        "language": language,
        "code": code,
        "status": "pending",
        "score": 0,
        "total_score": 0,
        "testcases": []
    }
    asyncio.create_task(run_judge_task(submission_id))
    return submission_id

def get_submission(submission_id: str) -> Optional[Dict]:
    return _submissions.get(submission_id)

async def run_judge_task(submission_id: str) -> None:
    submission = _submissions.get(submission_id)
    if not submission:
        return
    try:
        problem = load_problem(submission["problem_id"])
        if not problem:
            submission["status"] = "error"
            submission["info"]="problem not found"
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
        for tc in testcases:
            result = await judge_single_testcase(
                code=submission["code"],
                language=submission["language"],
                input_data=tc["input"],
                expected_output=tc["output"],
                time_limit=time_limit,
                memory_limit=memory_limit
            )
            submission["testcases"].append(result)
            if result["status"] == "AC":
                passed_count += 1
        submission["score"] = passed_count * 10
        submission["status"] = "success"
    except Exception as e:
        submission["status"] = "error"
        submission["info"] = str(e)