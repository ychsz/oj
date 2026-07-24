from __future__ import annotations
import os
import sys
import time
from typing import Any, Dict, List, Optional
import streamlit as st

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from frontend import api_client, config
from frontend.api_client import ApiError

st.set_page_config(
    page_title="Online Judge",
    page_icon="🧑‍💻",
    layout="wide",
    initial_sidebar_state="expanded",
)

def init_state() -> None:
    defaults = {
        "backend_url": config.DEFAULT_BACKEND,
        "user": None,
        "view_problem_id": None,
        "fresh_submission_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def is_logged_in() -> bool:
    return st.session_state.get("user") is not None

def current_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("user")

def is_admin() -> bool:
    u = current_user()
    return bool(u) and u.get("role") == "admin"

def show_api_error(e: ApiError, prefix: str = "Operation failed") -> None:
    code_part = f" (HTTP {e.code})" if e.code is not None else ""
    st.error(f"{prefix}{code_part}: {e.msg}")

def submission_status_badge(status: str) -> str:
    return config.SUBMISSION_STATUS_LABEL.get(status, status)

def safe_call(fn, *args, prefix: str = "Operation failed", **kwargs):
    try:
        return fn(*args, **kwargs)
    except ApiError as e:
        show_api_error(e, prefix)
        return None
    except Exception as e:
        st.error(f"{prefix}: {e}")
        return None

def _lang_id_to_name() -> Dict[str, str]:
    langs = safe_call(api_client.list_languages, prefix="Failed to load languages") or []
    return {l["id"]: l["name"] for l in langs}

def _lang_for_stcode(lang_id: str) -> str:
    lid = (lang_id or "").lower()
    if lid in ("python", "py", "python3"):
        return "python"
    if lid in ("cpp", "c++", "cxx", "cc"):
        return "cpp"
    if lid == "c":
        return "c"
    if lid == "java":
        return "java"
    if lid in ("javascript", "js"):
        return "javascript"
    return lid

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🧑‍💻 Online Judge")

        st.text_input(
            "Backend URL",
            key="backend_url",
            help="FastAPI backend root URL, default http://localhost:8000",
        )
        if st.button("🔗 Test connection", use_container_width=True):
            ok = safe_call(api_client.list_languages, prefix="Connection failed")
            if ok is not None:
                st.success(f"✅ Connected to {api_client.get_backend()}")
        st.divider()
        if not is_logged_in():
            render_login_form()
        else:
            render_user_card()

def render_login_form() -> None:
    st.markdown("### 🔐 Login")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                data = safe_call(
                    api_client.login, username, password, prefix="Login failed"
                )
                if data is not None:
                    # The login API only returns {user_id, username, role};
                    # call get_user to fill in submit_count/resolve_count/join_time.
                    full = safe_call(api_client.get_user, data["user_id"],
                                     prefix="Failed to fetch user info")
                    st.session_state.user = full if full is not None else data
                    st.success(f"Welcome, {data.get('username')}!")
                    st.rerun()
    with st.expander("📝 Register a new account"):
        with st.form("register_form"):
            r_user = st.text_input("New username", key="reg_username",
                                   help="3-40 characters")
            r_pass = st.text_input("New password (>= 6 chars)", type="password",
                                   key="reg_password")
            r_submit = st.form_submit_button("Register", use_container_width=True)
            if r_submit:
                if not r_user or not r_pass:
                    st.error("Please fill in both username and password")
                else:
                    data = safe_call(
                        api_client.register, r_user, r_pass, prefix="Registration failed"
                    )
                    if data is not None:
                        st.success("Registration successful. Please log in with the new account.")
    st.markdown("Author: Yuan Chenhao")
    st.markdown("Contact: 19924573320")
    st.markdown("weixin: yuanchenhao_sz")

def render_user_card() -> None:
    u = current_user()
    st.markdown("### 👤 Current user")
    st.markdown(f"**Username**: {u.get('username')}")
    role = u.get("role", "user")
    role_emoji = {"admin": "🛡 Admin", "user": "🙋 User", "banned": "🚫 Banned"}.get(role, role)
    st.markdown(f"**Role**: {role_emoji}")
    st.markdown(f"**User ID**: `{u.get('user_id')}`")
    st.markdown(f"**Submissions**: {u.get('submit_count', 0)} ｜ **Solved**: {u.get('resolve_count', 0)}")
    st.markdown(f"**Joined**: {u.get('join_time', '-')}")

    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        api_client.logout()
        st.session_state.user = None
        st.session_state.fresh_submission_id = None
        st.rerun()

def tab_problems() -> None:
    st.header("📚 Problems")
    problems = safe_call(api_client.list_problems, prefix="Failed to load problems")
    if problems is None:
        return
    if not problems:
        st.info("No problems available.")
        return
    st.caption(f"{len(problems)} problem(s) in total. Pick one below to view details and submit.")
    rows = []
    for p in problems:
        rows.append({"ID": p.get("id", ""), "Title": p.get("title", "")})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("View a problem")
    options = [f"{p.get('id')}  {p.get('title')}" for p in problems]
    choice = st.selectbox("Select a problem", options=options, index=0)
    if st.button("📖 Open problem & submit", type="primary"):
        sel_id = choice.split("  ", 1)[0] if "  " in choice else choice
        st.session_state.view_problem_id = sel_id

def tab_submit() -> None:
    st.header("📝 Problem detail & submit")
    pid = st.session_state.get("view_problem_id")
    if not pid:
        st.info("Please pick a problem first on the \"Problems\" tab.")
        return
    problem = safe_call(api_client.get_problem, pid, prefix="Failed to load problem")
    if problem is None:
        return
    render_problem_detail(problem)
    st.divider()
    render_submit_form(problem)

def render_problem_detail(problem: Dict[str, Any]) -> None:
    pid = problem.get("id", "unknown")
    st.subheader(f"{problem.get('id')}  {problem.get('title')}")
    if problem.get("difficulty"):
        st.caption(f"Difficulty: {problem['difficulty']}")
    tags = problem.get("tags") or []
    if tags:
        st.caption("Tags: " + "  ·  ".join(tags))
    c1, c2, c3 = st.columns(3)
    c1.metric("Time limit", f"{problem.get('time_limit', '-')} s")
    c2.metric("Memory limit", f"{problem.get('memory_limit', '-')} MB")
    c3.metric("Testcases", f"{len(problem.get('testcases', []))}")
    st.markdown("**Description**")
    st.markdown(problem.get("description", "(none)") or "(none)")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Input**")
        st.markdown(problem.get("input_description", "") or "(none)")
    with col_b:
        st.markdown("**Output**")
        st.markdown(problem.get("output_description", "") or "(none)")
    samples = problem.get("samples") or []
    if samples:
        st.markdown("**Samples**")
        for i, s in enumerate(samples, start=1):
            st.markdown(f"**Sample {i}**")
            sc1, sc2 = st.columns(2)
            sc1.text_area("Input", s.get("input", ""), height=80,
                          key=f"sample_in_{i}_{pid}", disabled=True)
            sc2.text_area("Output", s.get("output", ""), height=80,
                          key=f"sample_out_{i}_{pid}", disabled=True)

    if problem.get("constraints"):
        st.markdown("**Constraints**")
        st.markdown(problem["constraints"])
    if problem.get("hint"):
        st.markdown("**Hint**")
        st.markdown(problem["hint"])
    if problem.get("source"):
        st.caption(f"Source: {problem['source']}")
    if problem.get("author"):
        st.caption(f"Author: {problem['author']}")

def render_submit_form(problem: Dict[str, Any]) -> None:
    st.subheader("🚀 Submit code")
    langs = safe_call(api_client.list_languages, prefix="Failed to load languages") or []
    if not langs:
        st.warning("The backend has no languages configured; cannot submit.")
        return
    lang_options = {f"{l['name']}  ({l['id']})": l["id"] for l in langs}
    lang_label = st.selectbox("Select language", list(lang_options.keys()))
    lang_id = lang_options[lang_label]
    default_code = ""
    code = st.text_area(
        "Code", value=default_code, height=320,
        key=f"code_{problem['id']}_{lang_id}",
    )
    if st.button("📤 Submit", type="primary", use_container_width=True):
        if not code.strip():
            st.error("Code cannot be empty")
            return
        data = safe_call(
            api_client.submit, problem["id"], lang_id, code, prefix="Submission failed"
        )
        if data is not None:
            sub_id = data.get("submission_id")
            st.session_state.fresh_submission_id = sub_id
            st.success(f"Submitted! submission_id = `{sub_id}`, judging...")
            st.rerun()

def tab_result() -> None:
    st.header("⏳ Submission result")
    sub_id = st.session_state.get("fresh_submission_id")
    if not sub_id:
        st.info("No freshly submitted record yet. Submit code on the "
                "\"Problem detail & submit\" tab, or view history on the "
                "\"My submissions\" tab.")
        return
    st.caption(f"submission_id: `{sub_id}`")
    col_poll, col_skip = st.columns([1, 3])
    with col_poll:
        auto_poll = st.toggle("Auto-poll", value=True,
                              help="Keep querying the verdict until finished")
    if st.session_state.get("_poll_done_" + str(sub_id), False) or not auto_poll:
        if not auto_poll:
            if st.button("🔄 Refresh"):
                st.rerun()
        render_submission_detail(sub_id)
        return
    status = poll_submission(sub_id)
    if status is None:
        render_submission_detail(sub_id)
        return
    if status in ("success", "error"):
        st.session_state["_poll_done_" + str(sub_id)] = True
        render_submission_detail(sub_id)
    else:
        with st.spinner("Judging, please wait..."):
            time.sleep(1.5)
        st.rerun()

def poll_submission(sub_id: str) -> Optional[str]:
    u = current_user()
    if u is None:
        return None
    res = safe_call(
        api_client.list_submissions, user_id=u["user_id"], prefix="Failed to query status"
    )
    if res is None:
        return None
    for s in res.get("submissions", []):
        if s.get("submission_id") == sub_id:
            return s.get("status")
    return None

def render_submission_detail(sub_id: str) -> None:
    basic = safe_call(api_client.get_submission, sub_id, prefix="Failed to read result")
    if basic is None:
        return
    problem_id = basic.get("problem_id", "")
    problem_title = basic.get("problem_title", "")
    lang_id = basic.get("language", "")
    code = basic.get("code", "")
    lang_map = _lang_id_to_name()
    lang_display = lang_map.get(lang_id, lang_id)
    st.subheader(f"{problem_id}  {problem_title}".strip())
    st.caption(f"Language: {lang_display}  ·  submission_id: `{sub_id}`")
    if code:
        st.markdown("**Source code**")
        st.code(code, language=_lang_for_stcode(lang_id))
    else:
        st.caption("Source code unavailable.")
    st.divider()
    status = poll_submission(sub_id) or "pending"
    badge = submission_status_badge(status)
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", badge)
    c2.metric("Score", basic.get("score", 0))
    c3.metric("Total", basic.get("counts", 0))
    if status == "pending":
        st.info("Still judging...")
        return
    if status == "error":
        st.error("Evaluation ended abnormally. This may be caused by a "
                 "compilation error or a runtime environment issue.")
        return
    st.divider()
    st.subheader("🧪 Testcase details")
    log = safe_call(api_client.get_submission_log, sub_id, prefix="Failed to read log")
    if log is None:
        return
    details = log.get("details", []) or []
    if not details:
        st.warning("No testcase details available.")
        return
    row_size = 8
    for start in range(0, len(details), row_size):
        chunk = details[start:start + row_size]
        cs = st.columns(len(chunk))
        for cell, d in zip(cs, chunk):
            r = str(d.get("result", "?"))
            color = config.RESULT_COLOR.get(r, "grey")
            emoji = config.RESULT_EMOJI.get(r, "❓")
            label = config.RESULT_LABEL.get(r, r)
            t = d.get("time", 0)
            m = d.get("memory", 0)
            cell.markdown(
                f"**#{d.get('id')}**  {emoji}\n\n"
                f":{color}[{label}]\n\n"
                f"⏱ {t} s\n\n💾 {m} MB"
            )
    st.divider()
    c_ok = sum(1 for d in details if str(d.get("result")) == "AC")
    st.success(f"Passed {c_ok} / {len(details)} testcases, "
               f"score {log.get('score', 0)} / {log.get('counts', 0)}")

def tab_my_submissions() -> None:
    st.header("📋 My submissions")
    u = current_user()
    if u is None:
        st.warning("Please log in first.")
        return
    res = safe_call(
        api_client.list_submissions, user_id=u["user_id"], prefix="Failed to load history"
    )
    if res is None:
        return
    rows = res.get("submissions", []) or []
    if not rows:
        st.info("No submissions yet.")
        return
    lang_map = _lang_id_to_name()
    table_rows = []
    for s in rows:
        sid = s.get("submission_id")
        status = s.get("status", "")
        problem_id = s.get("problem_id", "")
        problem_title = s.get("problem_title", "")
        lang_id = s.get("language", "")
        lang_display = lang_map.get(lang_id, lang_id)
        if status == "success":
            score_display = f"{s.get('score', 0)}/{s.get('counts', 0)}"
        elif status == "error":
            score_display = "Error"
        else:
            score_display = "Judging"
        table_rows.append({
            "submission_id": sid,
            "Problem": f"{problem_id}  {problem_title}".strip(),
            "Language": lang_display,
            "Status": submission_status_badge(status),
            "Score": score_display,
        })
    st.dataframe(table_rows, use_container_width=True, hide_index=True)
    st.caption(f"{res.get('total', len(rows))} record(s) in total.")
    st.divider()
    st.subheader("View a submission's details")
    options = [
        f"{s.get('submission_id')}  [{submission_status_badge(s.get('status',''))}]  "
        f"{s.get('problem_id','')}  {s.get('problem_title','')}".rstrip()
        for s in rows
    ]
    if not options:
        return
    choice = st.selectbox("Select submission_id", options=options)
    sel_id = choice.split("  ", 1)[0] if "  " in choice else choice
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("📂 View on result tab", type="primary"):
            st.session_state.fresh_submission_id = sel_id
            st.session_state.pop("_poll_done_" + str(sel_id), None)
            st.rerun()
    with c1:
        if st.checkbox("Show details inline", key=f"show_detail_{sel_id}"):
            render_submission_detail(sel_id)

def tab_admin() -> None:
    st.header("🛡 Admin panel")
    if not is_admin():
        st.warning("This panel is restricted to administrators.")
        return
    sub1, sub2, sub3, sub4 = st.tabs(
        ["👥 Users", "🔁 Rejudge", "📜 Audit log", "💾 Export / Import / Reset"]
    )
    with sub1:
        admin_users()
    with sub2:
        admin_rejudge()
    with sub3:
        admin_audit()
    with sub4:
        admin_system()

def admin_users() -> None:
    st.subheader("User list")
    res = safe_call(api_client.list_users, prefix="Failed to load users")
    if res is None:
        return
    users: List[Dict[str, Any]] = res.get("users", []) or []
    if not users:
        st.info("No users.")
        return
    st.dataframe(
        [{"Username": u.get("username"), "ID": u.get("user_id"),
          "Role": u.get("role"), "Submits": u.get("submit_count"),
          "Solved": u.get("resolve_count"), "Joined": u.get("join_time")}
         for u in users],
        use_container_width=True, hide_index=True,
    )
    st.divider()
    st.markdown("#### Change user role")
    uname_map = {f"{u.get('username')}  ({u.get('user_id')})": u.get("user_id")
                 for u in users}
    choice = st.selectbox("Select user", list(uname_map.keys()))
    uid = uname_map.get(choice)
    new_role = st.selectbox("New role", ["user", "admin", "banned"])
    if st.button("Apply", type="primary"):
        data = safe_call(api_client.change_user_role, uid, new_role,
                         prefix="Failed to change role")
        if data is not None:
            st.success(f"Changed role of {choice} to {new_role}")
            st.rerun()
    st.divider()
    st.markdown("#### Create administrator")
    with st.form("create_admin_form"):
        a_user = st.text_input("Username")
        a_pass = st.text_input("Password", type="password")
        a_sub = st.form_submit_button("Create", type="primary")
        if a_sub:
            if not a_user or not a_pass:
                st.error("Please fill in both username and password")
            else:
                data = safe_call(api_client.create_admin, a_user, a_pass,
                                 prefix="Failed to create")
                if data is not None:
                    st.success(f"Admin {data.get('username')} created")
                    st.rerun()

def admin_rejudge() -> None:
    st.subheader("Rejudge a submission")
    sid = st.text_input("submission_id")
    if st.button("🔁 Trigger rejudge", type="primary"):
        if not sid.strip():
            st.error("Please enter a submission_id")
            return
        data = safe_call(api_client.rejudge, sid.strip(), prefix="Rejudge failed")
        if data is not None:
            st.success(f"Rejudge triggered: {sid.strip()} (status reset to pending)")

def admin_audit() -> None:
    st.subheader("Audit log")
    res = safe_call(api_client.list_audit, prefix="Failed to load audit log")
    if res is None:
        return
    logs = res.get("logs", []) or []
    if not logs:
        st.info("No audit logs.")
        return
    st.dataframe(
        [{"Time": l.get("time", ""), "User": l.get("user_id", ""),
          "Problem": l.get("problem_id", ""), "Action": l.get("action", ""),
          "Status": l.get("status", "")}
         for l in logs],
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{res.get('total', len(logs))} record(s) in total.")

def admin_system() -> None:
    st.subheader("Export data")
    if st.button("⬇ Export as JSON"):
        data = safe_call(api_client.export_data, prefix="Export failed")
        if data is not None:
            import json
            st.download_button(
                "💾 Download export.json",
                data=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="export.json",
                mime="application/json",
            )
    st.divider()
    st.subheader("Import data")
    up = st.file_uploader("Upload export.json", type=["json"])
    if up is not None and st.button("⬆ Import", type="primary"):
        ok = safe_call(
            api_client.import_data, up.getvalue(), up.name, prefix="Import failed"
        )
        if ok is not None:
            st.success("Import succeeded.")
    st.divider()
    st.subheader("⚠ System reset")
    st.warning("This will wipe all users / problems / submissions / audit logs "
               "/ language configs and cannot be undone!")
    confirm = st.checkbox("I confirm I want to reset the entire system")
    if st.button("🗑 Reset system", type="primary", disabled=not confirm):
        ok = safe_call(api_client.reset_system, prefix="Reset failed")
        if ok is not None:
            st.session_state.user = None
            st.session_state.fresh_submission_id = None
            st.success("System reset; the current session has been logged out.")
            st.rerun()

def main() -> None:
    tabs = ["📚 Problems", "📝 Problem detail & submit", "⏳ Submission result", "📋 My submissions"]
    if is_admin():
        tabs.append("🛡 Admin")
    selected = st.tabs(tabs)
    with selected[0]:
        tab_problems()
    with selected[1]:
        tab_submit()
    with selected[2]:
        tab_result()
    with selected[3]:
        tab_my_submissions()
    if len(selected) > 4:
        with selected[4]:
            tab_admin()

if __name__ == "__main__":
    render_sidebar()
    if not is_logged_in():
        st.markdown("## 👋 Welcome to the Online Judge")
        st.markdown("Please **log in** from the sidebar to get started.")
    else:
        main()
