from fastapi import APIRouter, Request
from app.auth import require_admin
import json
import os

router = APIRouter()

LOG_DIR = os.path.join("E:", os.sep, "MY-Shop", "python-version", "logs")

def _read_json(cat):
    f = os.path.join(LOG_DIR, cat + ".json")
    if not os.path.isfile(f):
        return []
    fh = open(f, "r", encoding="utf-8")
    try:
        data = json.load(fh)
    except:
        data = []
    fh.close()
    return data

def _do_cleanup(days=30):
    import datetime
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    for cat in ["user_login", "admin_login", "user_action", "admin_action", "server"]:
        f = os.path.join(LOG_DIR, cat + ".json")
        if not os.path.isfile(f):
            continue
        try:
            fh = open(f, "r", encoding="utf-8")
            logs = json.load(fh)
            fh.close()
            filtered = [l for l in logs if l.get("time", "") >= cutoff]
            if len(filtered) != len(logs):
                fh = open(f, "w", encoding="utf-8")
                json.dump(filtered, fh, ensure_ascii=False)
                fh.close()
        except:
            pass

@router.get("/api/admin/logs")
async def get_logs(request: Request, category: str = "all", page: int = 1, page_size: int = 50, level: str = "", sort: str = "time_desc"):
    await require_admin(request)
    cats = ["server", "user_login", "admin_login", "user_action", "admin_action"] if category == "all" else [category]
    all_logs = []
    for cat in cats:
        entries = _read_json(cat)
        if category == "all":
            for entry in entries:
                entry["category"] = cat
                all_logs.append(entry)
        else:
            all_logs.extend(entries)
    if level:
        all_logs = [l for l in all_logs if l.get("level") == level]
    all_logs.sort(key=lambda x: x.get("time", ""), reverse=(sort != "time_asc"))
    total = len(all_logs)
    items = all_logs[(page - 1) * page_size: page * page_size]
    return {"total": total, "page": page, "page_size": page_size, "logs": items}

@router.get("/api/admin/logs/retention")
async def get_retention(request: Request):
    await require_admin(request)
    from app.models import AppSetting
    from app.database import engine
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        row = s.query(AppSetting).filter(AppSetting.key == "log_retention_days").first()
        days = int(row.value) if row and row.value else 30
    return {"retention_days": days}

@router.post("/api/admin/logs/retention")
async def set_retention(data: dict, request: Request):
    await require_admin(request)
    from app.models import AppSetting
    from app.database import engine
    from sqlalchemy.orm import Session
    days = data.get("retention_days", 30)
    with Session(engine) as s:
        row = s.query(AppSetting).filter(AppSetting.key == "log_retention_days").first()
        if row:
            row.value = str(days)
        else:
            s.add(AppSetting(key="log_retention_days", value=str(days)))
        s.commit()
    _do_cleanup(days)
    return {"message": "已保存"}

@router.post("/api/admin/logs/cleanup")
async def manual_cleanup(request: Request):
    await require_admin(request)
    from app.models import AppSetting
    from app.database import engine
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        row = s.query(AppSetting).filter(AppSetting.key == "log_retention_days").first()
        days = int(row.value) if row and row.value else 30
    _do_cleanup(days)
    return {"message": "已清理过期日志"}
