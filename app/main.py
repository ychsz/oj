import asyncio
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from app.problem_manager import (
    get_problem_list,
    load_problem,
    add_problem,
    delete_problem
)
from app.language_manager import get_all_languages, register_language, get_language_config
from app.submission_manager import create_submission, get_submission,get_submission_list,rejudge_submission

app = FastAPI(title="oj")

class SampleItem(BaseModel):
    input: str
    output: str

class ProblemCreate(BaseModel):
    id: str
    title: str
    description: str
    input_description: str
    output_description: str
    samples: List[SampleItem]
    constraints: str
    testcases: List[SampleItem]
    hint: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    time_limit: Optional[float] = None
    memory_limit: Optional[int] = None
    author: Optional[str] = None
    difficulty: Optional[str] = None

class SubmissionCreate(BaseModel):
    problem_id: str
    language: str
    code: str

class LanguageRegister(BaseModel):
    name: str
    file_ext:str
    compile_cmd: Optional[str] = None
    run_cmd: str
    time_limit: Optional[float] = None
    memory_limit: Optional[int] = None

def make_response(code: int, msg: str, data=None) -> JSONResponse:
    content = {
        "code": code,
        "msg": msg,
        "data": data
    }
    return JSONResponse(status_code=code, content=content)

def get_current_user(request: Request) -> tuple[str, bool]:
    user_id = request.headers.get("X-User-ID", "guest")
    is_admin = request.headers.get("X-Is-Admin", "0") == "1"
    return user_id, is_admin

@app.get("/api/problems/")
async def get_problems():
    problems = get_problem_list()
    return make_response(200, "success", problems)

@app.get("/api/problems/{problem_id}")
async def get_problem_detail(problem_id: str):
    problem = load_problem(problem_id)
    if problem is None:
        return make_response(404, "problem not found", None)
    return make_response(200, "success", problem)

@app.post("/api/problems/")
async def create_problem(problem: ProblemCreate):
    problem_dict = problem.model_dump()
    success, msg, problem_id = add_problem(problem_dict)
    if not success:
        if "problem id already exists" == msg:
            return make_response(409, msg, None)
        else:
            return make_response(400, msg, None)
    return make_response(200, msg, {"id": problem_id})

@app.delete("/api/problems/{problem_id}")
async def delete_problem_api(problem_id: str,request:Request):
    _, is_admin = get_current_user(request)
    if not is_admin:
        return make_response(403, "permission denied", None)
    if load_problem(problem_id) is None:
        return make_response(404, "problem not found", None)
    else:
        delete_problem(problem_id)
        return make_response(200, "delete success", {"id": problem_id})

@app.get("/api/languages/")
async def list_languages():
    langs = get_all_languages()
    return make_response(200, "success", langs)

@app.post("/api/languages/")
async def add_language(lang: LanguageRegister,request:Request):
    current_user, _ = get_current_user(request)
    if current_user == "guest":
        return make_response(401, "not logged in", None)
    success = register_language(
        lang_id=lang.id,
        name=lang.name,
        compile_cmd=lang.compile_cmd,
        run_cmd=lang.run_cmd,
        file_suffix=lang.file_suffix,
        default_time_limit=lang.default_time_limit,
        default_memory_limit=lang.default_memory_limit
    )
    if not success:
        return make_response(409, "language id already exists", None)
    return make_response(200, "register success", {"id": lang.id})

@app.post("/api/submissions/")
async def submit_code(submission: SubmissionCreate,request:Request):
    current_user, _ = get_current_user(request)
    if not load_problem(submission.problem_id):
        return make_response(404, "problem not found", None)
    if not get_language_config(submission.language):
        return make_response(404, "language not supported", None)
    submission_id = create_submission(
        problem_id=submission.problem_id,
        language=submission.language,
        code=submission.code,
        user_id=current_user
    )
    return make_response(200, "success", {
        "submission_id": submission_id,
        "status": "pending"
    })

@app.get("/api/submissions/{submission_id}")
async def get_submission_result(submission_id: str,request:Request):
    current_user, is_admin = get_current_user(request)
    sub = get_submission(submission_id)
    if not sub:
        return make_response(404, "submission not found", None)
    if not is_admin and sub["user_id"] != current_user:
        return make_response(403, "permission denied", None)
    return make_response(200, "success", {
        "score": sub["score"],
        "counts": sub["total_score"]
    })

@app.get("/api/submissions/")
async def list_submissions(
        request: Request,
        user_id: Optional[str] = None,
        problem_id: Optional[str] = None,
        status: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None
):
    current_user, is_admin = get_current_user(request)
    if user_id is None:
        if not is_admin:
            user_id = current_user
    if user_id is None and problem_id is None:
        return make_response(400, "user_id and problem_id cannot both be empty", None)
    if page is not None and page_size is None:
        return make_response(400, "page_size is required when page is provided", None)
    total, subs = get_submission_list(
        user_id=user_id,
        problem_id=problem_id,
        status=status,
        page=page,
        page_size=page_size
    )
    result_list = []
    for sub in subs:
        item = {
            "submission_id": sub["id"],
            "status": sub["status"]
        }
        if sub["status"] == "success":
            item["score"] = sub["score"]
            item["counts"] = sub["total_score"]
        result_list.append(item)
    return make_response(200, "success", {
        "total": total,
        "submissions": result_list
    })

@app.put("/api/submissions/{submission_id}/rejudge")
async def rejudge_submission_api(submission_id: str, request: Request):
    _, is_admin = get_current_user(request)
    if not is_admin:
        return make_response(403, "permission denied", None)
    sub = get_submission(submission_id)
    if not sub:
        return make_response(404, "submission not found", None)
    await rejudge_submission(submission_id)
    return make_response(200, "rejudge started", {
        "submission_id": submission_id,
        "status": "pending"
    })