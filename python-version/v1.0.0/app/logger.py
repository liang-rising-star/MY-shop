import json
import os
import time
import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def _get_file(category: str) -> Path:
    return LOG_DIR / f"{category}.json"

def _read(category: str) -> list:
    f = _get_file(category)
    if not f.exists():
        return []
    try:
        with open(f, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except:
        return []

def _write(category: str, data: list):
    with open(_get_file(category), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)

def add_log(category: str, level: str, operator: str, operator_role: str, action: str, detail: str = "", extra: dict = None):
    entry = {
        "id": int(time.time() * 1000),
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "level": level,
        "operator": operator,
        "operator_role": operator_role,
        "action": action,
        "detail": detail,
    }
    if extra:
        entry.update(extra)
    logs = _read(category)
    logs.insert(0, entry)
    _write(category, logs)

def log_user_login(username: str, ip: str, success: bool, reason: str = ""):
    add_log("user_login",
            "success" if success else "error",
            username, "用户",
            "登录" + ("成功" if success else "失败"),
            f"IP: {ip}" + (f"，原因: {reason}" if reason else ""))

def log_admin_login(username: str, ip: str, success: bool, is_super: bool = False, reason: str = ""):
    role = "超级管理员" if is_super else "管理员"
    add_log("admin_login",
            "success" if success else "error",
            username, role,
            "登录" + ("成功" if success else "失败"),
            f"IP: {ip}" + (f"，原因: {reason}" if reason else ""))

def log_user_action(username: str, action: str, detail: str = ""):
    add_log("user_action", "info", username, "用户", action, detail)

def log_admin_action(admin_name: str, is_super: bool, action: str, detail: str = ""):
    role = "超级管理员" if is_super else "管理员"
    add_log("admin_action", "info", admin_name, role, action, detail)

def log_server(level: str, message: str, detail: str = ""):
    add_log("server", level, "系统", "系统", message, detail)

def get_logs(category: str = "all", page: int = 1, page_size: int = 50, level: str = "", sort: str = "time_desc") -> dict:
    if category == "all":
        all_logs = []
        for cat in ["server", "user_login", "admin_login", "user_action", "admin_action"]:
            for entry in _read(cat):
                all_logs.append(entry)
    else:
        all_logs = _read(category)

    if level:
        all_logs = [l for l in all_logs if l.get("level") == level]

    if sort == "time_asc":
        all_logs.sort(key=lambda x: x.get("time", ""))
    else:
        all_logs.sort(key=lambda x: x.get("time", ""), reverse=True)

    total = len(all_logs)
    start = (page - 1) * page_size
    items = all_logs[start:start + page_size]
    return {"total": total, "page": page, "page_size": page_size, "logs": items}

def cleanup_expired(retention_days: int = 30):
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
    for cat in ["user_login", "admin_login", "user_action", "admin_action", "server"]:
        logs = _read(cat)
        filtered = [l for l in logs if l.get("time", "") >= cutoff]
        if len(filtered) != len(logs):
            _write(cat, filtered)
