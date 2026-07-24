from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import requests
import streamlit as st
from frontend import config

class ApiError(Exception):
    def __init__(self, msg: str, code: Optional[int] = None):
        super().__init__(msg)
        self.msg = msg
        self.code = code

def get_http_session() -> requests.Session:
    if "http_session" not in st.session_state:
        st.session_state["http_session"] = requests.Session()
    return st.session_state["http_session"]

def reset_http_session() -> None:
    if "http_session" in st.session_state:
        st.session_state["http_session"].cookies.clear()
    st.session_state.pop("http_session", None)

def get_backend() -> str:
    return st.session_state.get("backend_url", config.DEFAULT_BACKEND).rstrip("/")

def _url(path_key: str, **path_params) -> str:
    raw = config.PATHS[path_key]
    if path_params:
        raw = raw.format(**path_params)
    return f"{get_backend()}{config.API_PREFIX}{raw}"

def api_request(
    method: str,
    path_key: str,
    *,
    path_params: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
) -> Tuple[int, str, Any]:
    sess = get_http_session()
    url = _url(path_key, **(path_params or {}))
    try:
        resp = sess.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            files=files,
            timeout=timeout,
        )
    except requests.exceptions.ConnectionError as e:
        raise ApiError(f"Cannot connect to backend {get_backend()}: {e.__class__.__name__}", None) from e
    except requests.exceptions.Timeout as e:
        raise ApiError("Backend request timed out, please retry later", None) from e
    except requests.exceptions.RequestException as e:
        raise ApiError(f"Network request failed: {e.__class__.__name__}", None) from e
    try:
        body = resp.json()
    except ValueError:
        raise ApiError(f"Backend returned non-JSON (HTTP {resp.status_code})", resp.status_code)
    code = body.get("code")
    msg = body.get("msg") or "Unknown error"
    data = body.get("data")
    if code is None:
        raise ApiError("Backend response missing code field", resp.status_code)
    return code, msg, data

def _call(method: str, path_key: str, **kwargs) -> Any:
    code, msg, data = api_request(method, path_key, **kwargs)
    if code != 200:
        raise ApiError(msg, code)
    return data

def login(username: str, password: str) -> Dict[str, Any]:
    return _call("POST", "login", json_body={"username": username, "password": password})

def logout() -> None:
    try:
        _call("POST", "logout")
    except ApiError:
        pass
    finally:
        reset_http_session()

def register(username: str, password: str) -> Dict[str, Any]:
    return _call("POST", "register", json_body={"username": username, "password": password})

def list_problems() -> list:
    return _call("GET", "list_problems") or []

def get_problem(problem_id: str) -> Dict[str, Any]:
    return _call("GET", "get_problem", path_params={"problem_id": problem_id})

def create_problem(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _call("POST", "create_problem", json_body=payload)

def delete_problem(problem_id: str) -> Dict[str, Any]:
    return _call("DELETE", "delete_problem", path_params={"problem_id": problem_id})

def get_spj_status(problem_id: str) -> Dict[str, Any]:
    """GET /api/problems/{id}/spj -- {uploaded, filename?, size?} (any logged-in user)."""
    return _call("GET", "spj", path_params={"problem_id": problem_id})

def upload_spj_script(problem_id: str, file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """POST /api/problems/{id}/spj -- admin only. Uploads a .py special judge script."""
    files = {"file": (filename, file_bytes, "text/x-python")}
    return _call("POST", "spj", path_params={"problem_id": problem_id}, files=files)

def delete_spj_script(problem_id: str) -> Dict[str, Any]:
    """DELETE /api/problems/{id}/spj -- admin only."""
    return _call("DELETE", "spj", path_params={"problem_id": problem_id})

def list_languages() -> Dict[str, list]:
    raw = _call("GET", "list_languages") or {}
    ids = raw.get("id", [])
    names = raw.get("name", [])
    tl = raw.get("default_time_limit", [])
    ml = raw.get("default_memory_limit", [])
    langs = []
    for i, lang_id in enumerate(ids):
        langs.append({
            "id": lang_id,
            "name": names[i] if i < len(names) else lang_id,
            "default_time_limit": tl[i] if i < len(tl) else None,
            "default_memory_limit": ml[i] if i < len(ml) else None,
        })
    return langs

def submit(problem_id: str, language: str, code: str) -> Dict[str, Any]:
    return _call("POST", "submit", json_body={
        "problem_id": problem_id,
        "language": language,
        "code": code,
    })

def get_submission(submission_id: str) -> Dict[str, Any]:
    return _call("GET", "get_submission", path_params={"submission_id": submission_id})

def list_submissions(
    user_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    status: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if user_id is not None:
        params["user_id"] = user_id
    if problem_id is not None:
        params["problem_id"] = problem_id
    if status is not None:
        params["status"] = status
    if page is not None:
        params["page"] = page
        params["page_size"] = page_size
    return _call("GET", "list_submissions", params=params) or {"total": 0, "submissions": []}

def get_submission_log(submission_id: str) -> Dict[str, Any]:
    """GET /api/submissions/{id}/log -- per-testcase details {details, score, counts}."""
    return _call("GET", "get_submission_log", path_params={"submission_id": submission_id})

def rejudge(submission_id: str) -> Dict[str, Any]:
    """PUT /api/submissions/{id}/rejudge -- admin only."""
    return _call("PUT", "rejudge", path_params={"submission_id": submission_id})

def get_user(user_id: str) -> Dict[str, Any]:
    return _call("GET", "get_user", path_params={"user_id": user_id})

def list_users(page: Optional[int] = None, page_size: Optional[int] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if page is not None:
        params["page"] = page
        params["page_size"] = page_size
    return _call("GET", "list_users", params=params) or {"total": 0, "users": []}

def change_user_role(user_id: str, role: str) -> Dict[str, Any]:
    return _call("PUT", "change_role",
                  path_params={"user_id": user_id}, json_body={"role": role})

def create_admin(username: str, password: str) -> Dict[str, Any]:
    return _call("POST", "create_admin",
                  json_body={"username": username, "password": password})

def list_audit(user_id: Optional[str] = None, problem_id: Optional[str] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if user_id is not None:
        params["user_id"] = user_id
    if problem_id is not None:
        params["problem_id"] = problem_id
    return _call("GET", "list_audit", params=params) or {"total": 0, "logs": []}

def reset_system() -> None:
    _call("POST", "reset")

def export_data() -> Dict[str, Any]:
    return _call("GET", "export") or {}

def import_data(file_bytes: bytes, filename: str) -> None:
    files = {"file": (filename, file_bytes, "application/json")}
    _call("POST", "import", files=files)