import uuid
from datetime import date
import bcrypt
import os
import json
from typing import Dict, Optional, List, Tuple
USER_DIR = "users"

def init_user_dir() -> None:
    if not os.path.exists(USER_DIR):
        os.makedirs(USER_DIR)

def get_user_file_path(user_id: str) -> str:
    return os.path.join(USER_DIR, f"{user_id}.json")

def save_user_to_file(user: Dict) -> None:
    file_path = get_user_file_path(user["user_id"])
    user_copy = user.copy()
    user_copy["resolved_problems"] = list(user["resolved_problems"])
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(user_copy, f, ensure_ascii=False, indent=2)

def load_user_from_file(user_id: str) -> Optional[Dict]:
    file_path = get_user_file_path(user_id)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        user = json.load(f)
    user["resolved_problems"] = set(user.get("resolved_problems", []))
    return user

def load_all_users() -> Tuple[Dict[str, Dict], Dict[str, str]]:
    users = {}
    username_map = {}
    for filename in os.listdir(USER_DIR):
        if filename.endswith(".json"):
            user_id = filename[:-5]
            user = load_user_from_file(user_id)
            users[user_id] = user
            username_map[user["username"]] = user_id
    return users, username_map

def init_default_admin() -> None:
    admin_username = "admin"
    admin_password = "admintestpassword"
    if admin_username in _username_map:
        return
    password_hash = bcrypt.hashpw(
        admin_password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")
    user_id = uuid.uuid4().hex
    _users[user_id] = {
        "user_id": user_id,
        "username": admin_username,
        "password_hash": password_hash,
        "role": "admin",
        "join_time": date.today().isoformat(),
        "submit_count": 0,
        "resolve_count": 0,
        "resolved_problems": set()
    }
    _username_map[admin_username] = user_id
    save_user_to_file(_users[user_id])

def register_user(username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    if len(username) < 3 or len(username) > 40:
        return False, "username length must be 3-40 characters", None
    if len(password) < 6:
        return False, "password must be at least 6 characters", None
    if username in _username_map:
        return False, "username already exists", None
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")
    user_id = uuid.uuid4().hex
    user = {
        "user_id": user_id,
        "username": username,
        "password_hash": password_hash,
        "role": "user",
        "join_time": date.today().isoformat(),
        "submit_count": 0,
        "resolve_count": 0,
        "resolved_problems": set()
    }
    _users[user_id] = user
    _username_map[username] = user_id
    save_user_to_file(user)
    public_user = _get_public_user_info(user)
    return True, "register success", public_user

def verify_login(username: str, password: str) -> Tuple[int, str, Optional[Dict]]:
    if username not in _username_map:
        bcrypt.checkpw(password.encode("utf-8"), _users[_username_map["admin"]]["password_hash"].encode("utf-8"))
        return 401, "invalid username or password", None
    user_id = _username_map[username]
    user = _users[user_id]
    password_correct = bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    )
    if not password_correct:
        return 401, "invalid username or password", None
    if user["role"] == "banned":
        return 403, "user is banned", None
    return 200, "login success", _get_public_user_info(user)

def get_user_by_id(user_id: str) -> Optional[Dict]:
    return _users.get(user_id)

def get_public_user_by_id(user_id: str) -> Optional[Dict]:
    user = _users.get(user_id)
    if not user:
        return None
    return _get_public_user_info(user)

def update_user_role(user_id: str, new_role: str) -> Tuple[bool, str]:
    valid_roles = {"user", "admin", "banned"}
    if new_role not in valid_roles:
        return False, "invalid role"
    user = _users.get(user_id)
    if not user:
        return False, "user not found"
    user["role"] = new_role
    save_user_to_file(user)
    return True, "role updated"

def get_user_list(page: Optional[int] = None, page_size: Optional[int] = None) -> Tuple[int, List[Dict]]:
    all_users = list(_users.values())
    total = len(all_users)
    if page is None and page_size is None:
        return total, [_get_public_user_info(u) for u in all_users]
    if page is None:
        page = 1
    start = (page - 1) * page_size
    end = start + page_size
    paginated = all_users[start:end]
    return total, [_get_public_user_info(u) for u in paginated]

def increment_submit_count(user_id: str) -> None:
    user = _users.get(user_id)
    if user:
        user["submit_count"] += 1
        save_user_to_file(user)

def increment_resolve_count(user_id: str, problem_id: str) -> None:
    user = _users.get(user_id)
    if not user:
        return
    if problem_id not in user["resolved_problems"]:
        user["resolved_problems"].add(problem_id)
        user["resolve_count"] += 1
        save_user_to_file(user)

def _get_public_user_info(user: Dict) -> Dict:
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "join_time": user["join_time"],
        "submit_count": user["submit_count"],
        "resolve_count": user["resolve_count"]
    }

def reset_users() -> None:
    global _users, _username_map
    for filename in os.listdir(USER_DIR):
        if filename.endswith(".json"):
            os.remove(os.path.join(USER_DIR, filename))
    _users.clear()
    _username_map.clear()
    init_default_admin()

def export_users() -> List[Dict]:
    result = []
    for user in _users.values():
        result.append({
            "user_id": user["user_id"],
            "username": user["username"],
            "password": user["password_hash"],
            "role": user["role"],
            "join_time": user["join_time"],
            "submit_count": user["submit_count"],
            "resolve_count": user["resolve_count"],
            "resolved_problems": list(user["resolved_problems"])
        })
    return result

def import_users(users_data: List[Dict]) -> None:
    global _users, _username_map
    for user_data in users_data:
        user_id = user_data["user_id"]
        user = {
            "user_id": user_id,
            "username": user_data["username"],
            "password_hash": user_data["password"],
            "role": user_data["role"],
            "join_time": user_data["join_time"],
            "submit_count": user_data["submit_count"],
            "resolve_count": user_data["resolve_count"],
            "resolved_problems": set(user_data.get("resolved_problems", []))
        }
        _users[user_id] = user
        _username_map[user_data["username"]] = user_id
        save_user_to_file(user)

init_user_dir()
_users,_username_map=load_all_users()
init_default_admin()