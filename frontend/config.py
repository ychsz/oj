DEFAULT_BACKEND = "http://localhost:8000"
API_PREFIX = "/api"

PATHS = {
    "login": "/auth/login",
    "logout": "/auth/logout",
    "register": "/users/",
    "list_problems": "/problems/",
    "get_problem": "/problems/{problem_id}",
    "create_problem": "/problems/",
    "delete_problem": "/problems/{problem_id}",
    "spj": "/problems/{problem_id}/spj",
    "list_languages": "/languages/",
    "submit": "/submissions/",
    "get_submission": "/submissions/{submission_id}",
    "list_submissions": "/submissions/",
    "get_submission_log": "/submissions/{submission_id}/log",
    "rejudge": "/submissions/{submission_id}/rejudge",
    "get_user": "/users/{user_id}",
    "list_users": "/users/",
    "change_role": "/users/{user_id}/role",
    "create_admin": "/users/admin",
    "list_audit": "/logs/access/",
    "reset": "/reset/",
    "export": "/export/",
    "import": "/import/",
}

RESULT_LABEL = {
    "AC": "Accepted",
    "WA": "Wrong Answer",
    "TLE": "Time Limit Exceeded",
    "MLE": "Memory Limit Exceeded",
    "RE": "Runtime Error",
    "CE": "Compilation Error",
    "UKE": "Unknown Error",
}

RESULT_COLOR = {
    "AC": "green",
    "WA": "red",
    "TLE": "yellow",
    "MLE": "yellow",
    "RE": "yellow",
    "CE": "yellow",
    "UKE": "grey",
}

RESULT_EMOJI = {
    "AC": "✅",
    "WA": "❌",
    "TLE": "⏱",
    "MLE": "💾",
    "RE": "💥",
    "CE": "🛠",
    "UKE": "❓",
}

SUBMISSION_STATUS_LABEL = {
    "pending": "Judging",
    "success": "Finished",
    "error": "Error",
}