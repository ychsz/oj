from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Optional,Dict,Tuple
from app.language_manager import get_all_languages, register_language, get_language_config
from app.submission_manager import create_submission, get_submission,get_submission_list,rejudge_submission
from app.audit_manager import add_audit_log, get_audit_log_list
from app.problem_manager import (
    get_problem_list,
    load_problem,
    add_problem,
    delete_problem,
    update_problem_log_visibility
)
from app.user_manager import (
    verify_login,
    register_user,
    get_user_by_id,
    get_public_user_by_id,
    update_user_role,
    get_user_list,
    increment_submit_count
)

app = FastAPI(title="oj")
app.add_middleware(SessionMiddleware, secret_key="complex-random-string")

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

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class RoleUpdateRequest(BaseModel):
    role: str

class CreateAdminRequest(BaseModel):
    username: str
    password: str

class LogVisibilityUpdate(BaseModel):
    public_cases: bool = False

def make_response(code: int, msg: str, data=None) -> JSONResponse:
    content = {
        "code": code,
        "msg": msg,
        "data": data
    }
    return JSONResponse(status_code=code, content=content)

def get_current_user(request: Request) -> Tuple[Optional[Dict], Optional[int], Optional[str]]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None, 401, "not logged in"
    user = get_user_by_id(user_id)
    if not user:
        request.session.clear()
        return None, 401, "not logged in"
    if user["role"] == "banned":
        return None, 403, "user is banned"
    return get_public_user_by_id(user_id), None, None

@app.get("/api/problems/")
async def get_problems(request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    problems = get_problem_list()
    return make_response(200, "success", problems)

@app.get("/api/problems/{problem_id}")
async def get_problem_detail(problem_id: str, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    problem = load_problem(problem_id)
    if problem is None:
        return make_response(404, "problem not found", None)
    return make_response(200, "success", problem)

@app.post("/api/problems/")
async def create_problem(problem: ProblemCreate, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    problem_dict = problem.model_dump()
    success, msg, problem_id = add_problem(problem_dict)
    if not success:
        if "problem id already exists" == msg:
            return make_response(409, msg, None)
        else:
            return make_response(400, msg, None)
    return make_response(200, msg, {"id": problem_id})

@app.delete("/api/problems/{problem_id}")
async def delete_problem_api(problem_id: str, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    if load_problem(problem_id) is None:
        return make_response(404, "problem not found", None)
    else:
        delete_problem(problem_id)
        return make_response(200, "delete success", {"id": problem_id})

@app.get("/api/languages/")
async def list_languages(request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    langs = get_all_languages()
    return make_response(200, "success", langs)

@app.post("/api/languages/")
async def add_language(lang: LanguageRegister, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    success = register_language(
        lang_id=lang.name,
        name=lang.name,
        compile_cmd=lang.compile_cmd,
        run_cmd=lang.run_cmd,
        file_suffix=lang.file_ext,
        default_time_limit=lang.time_limit,
        default_memory_limit=lang.memory_limit
    )
    if not success:
        return make_response(409, "language already exists", None)
    return make_response(200, "language registered", {"name": lang.name})

@app.post("/api/submissions/")
async def submit_code(submission: SubmissionCreate, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if not load_problem(submission.problem_id):
        return make_response(404, "problem not found", None)
    if not get_language_config(submission.language):
        return make_response(404, "language not supported", None)
    submission_id = create_submission(
        problem_id=submission.problem_id,
        language=submission.language,
        code=submission.code,
        user_id=current_user["user_id"]
    )
    increment_submit_count(current_user["user_id"])
    return make_response(200, "success", {
        "submission_id": submission_id,
        "status": "pending"
    })

@app.get("/api/submissions/{submission_id}")
async def get_submission_result(submission_id: str, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    sub = get_submission(submission_id)
    if not sub:
        return make_response(404, "submission not found", None)
    if current_user["role"] != "admin" and sub["user_id"] != current_user["user_id"]:
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
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if user_id is None:
        if current_user["role"] != "admin":
            user_id = current_user["user_id"]
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
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    sub = get_submission(submission_id)
    if not sub:
        return make_response(404, "submission not found", None)
    await rejudge_submission(submission_id)
    return make_response(200, "rejudge started", {
        "submission_id": submission_id,
        "status": "pending"
    })

@app.post("/api/auth/login")
async def login(request: Request, login_data: LoginRequest):
    code, msg, user = verify_login(login_data.username, login_data.password)
    if code != 200:
        return make_response(code, msg, None)
    request.session["user_id"] = user["user_id"]
    return make_response(200, msg, {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"]
    })

@app.post("/api/auth/logout")
async def logout(request: Request):
    user, err_code, err_msg = get_current_user(request)
    if not user:
        return make_response(err_code, err_msg, None)
    request.session.clear()
    return make_response(200, "logout success", None)

@app.post("/api/users/")
async def register(user_data: RegisterRequest):
    success, msg, user = register_user(user_data.username, user_data.password)
    if not success:
        return make_response(400, msg, None)
    return make_response(200, msg, user)

@app.get("/api/users/{user_id}")
async def get_user_info(user_id: str, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["user_id"] != user_id and current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    target_user = get_public_user_by_id(user_id)
    if not target_user:
        return make_response(404, "user not found", None)
    return make_response(200, "success", target_user)

@app.put("/api/users/{user_id}/role")
async def change_user_role(user_id: str, role_data: RoleUpdateRequest, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    success, msg = update_user_role(user_id, role_data.role)
    if not success:
        if msg == "user not found":
            return make_response(404, msg, None)
        else:
            return make_response(400, msg, None)
    return make_response(200, msg, {"user_id": user_id, "role": role_data.role})

@app.get("/api/users/")
async def list_users(
        request: Request,
        page: Optional[int] = None,
        page_size: Optional[int] = None
):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    if page is not None and page_size is None:
        return make_response(400, "page_size is required when page is provided", None)
    total, users = get_user_list(page, page_size)
    return make_response(200, "success", {
        "total": total,
        "users": users
    })

@app.post("/api/users/admin")
async def create_admin(admin_data: CreateAdminRequest, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    success, msg, user = register_user(admin_data.username, admin_data.password)
    if not success:
        return make_response(400, msg, None)
    update_user_role(user["user_id"], "admin")
    user["role"] = "admin"
    return make_response(200, "success", {"user_id": user["user_id"], "username": user["username"]})

@app.get("/api/submissions/{submission_id}/log")
async def get_submission_log(submission_id: str, request: Request):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    sub = get_submission(submission_id)
    if not sub:
        return make_response(404, "submission not found", None)
    problem = load_problem(sub["problem_id"])
    if not problem:
        return make_response(404, "problem not found", None)
    is_admin = current_user["role"] == "admin"
    is_owner = sub["user_id"] == current_user["user_id"]
    is_public = problem.get("public_cases", False)
    has_permission = is_admin or is_owner or is_public
    if not has_permission:
        add_audit_log(
            user_id=current_user["user_id"],
            problem_id=sub["problem_id"],
            action="view_log",
            status=403
        )
        return make_response(403, "permission denied", None)
    details = []
    for idx, testcase in enumerate(sub["testcases"], start=1):
        details.append({
            "id": idx,
            "result": testcase["status"],
            "time": round(testcase["time"], 2),
            "memory": round(testcase["memory"], 2)
        })
    add_audit_log(
        user_id=current_user["user_id"],
        problem_id=sub["problem_id"],
        action="view_log",
        status=200
    )
    return make_response(200, "success", {
        "details": details,
        "score": sub["score"],
        "counts": sub["total_score"]
    })

@app.put("/api/problems/{problem_id}/log_visibility")
async def update_log_visibility(
    problem_id: str,
    vis_data: LogVisibilityUpdate,
    request: Request
):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    success, msg = update_problem_log_visibility(problem_id, vis_data.public_cases)
    if not success:
        return make_response(404, msg, None)
    return make_response(200, msg, {
        "problem_id": problem_id,
        "public_cases": vis_data.public_cases
    })

@app.get("/api/logs/access/")
async def list_audit_logs(
    request: Request,
    user_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None
):
    current_user, err_code, err_msg = get_current_user(request)
    if not current_user:
        return make_response(err_code, err_msg, None)
    if current_user["role"] != "admin":
        return make_response(403, "permission denied", None)
    if page is not None and page_size is None:
        return make_response(400, "page_size is required when page is provided", None)
    total, logs = get_audit_log_list(
        user_id=user_id,
        problem_id=problem_id,
        page=page,
        page_size=page_size
    )
    return make_response(200, "success", {
        "total": total,
        "logs": logs
    })