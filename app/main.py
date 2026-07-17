from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from app.problem_manager import (
    get_problem_list,
    load_problem,
    add_problem,
    delete_problem
)

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

def make_response(code: int, msg: str, data=None) -> JSONResponse:
    content = {
        "code": code,
        "msg": msg,
        "data": data
    }
    return JSONResponse(status_code=code, content=content)

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
async def delete_problem_api(problem_id: str):
    if load_problem(problem_id) is None:
        return make_response(404, "problem not found", None)
    else:
        delete_problem(problem_id)
        return make_response(200, "delete success", {"id": problem_id})