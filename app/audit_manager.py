from datetime import datetime
from typing import List, Optional, Tuple,Dict

_audit_logs: List[Dict] = []

def add_audit_log(
    user_id: str,
    problem_id: str,
    action: str,
    status: int
) -> None:
    log_item = {
        "user_id": user_id,
        "problem_id": problem_id,
        "action": action,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
    }
    _audit_logs.insert(0, log_item)

def get_audit_log_list(
    user_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None
) -> Tuple[int, List[Dict]]:
    filtered = []
    for log in _audit_logs:
        if user_id is not None and log["user_id"] != user_id:
            continue
        if problem_id is not None and log["problem_id"] != problem_id:
            continue
        filtered.append(log)
    total_count = len(filtered)
    if page is None and page_size is None:
        return total_count, filtered
    if page is None:
        page = 1
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_logs = filtered[start_index:end_index]
    return total_count, paginated_logs

def reset_audit_logs() -> None:
    global _audit_logs
    _audit_logs.clear()