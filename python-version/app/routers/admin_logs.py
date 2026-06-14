import datetime
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import engine
from app.models import User, AdminLog, Dict
from app.auth import get_current_user, require_admin

router = APIRouter()

def add_admin_log(request: Request, action: str, target_type: str = "", target_id: int = None, message: str = ""):
    """添加管理员操作日志"""
    try:
        uid = request.state.user_id
        client_ip = request.client.host if request.client else ""
        with Session(engine) as s:
            log = AdminLog(
                admin_id=uid,
                action=action,
                target_type=target_type,
                target_id=target_id,
                message=message,
                ip_address=client_ip
            )
            s.add(log)
            s.commit()
    except:
        pass

@router.get("/api/admin/db-logs")
async def get_admin_db_logs(request: Request, page: int = 1, page_size: int = 20, action: str = ""):
    await require_admin(request)
    with Session(engine) as s:
        query = s.query(AdminLog).order_by(AdminLog.created_at.desc())
        if action:
            query = query.filter(AdminLog.action == action)
        total = query.count()
        logs = query.offset((page-1)*page_size).limit(page_size).all()
        
        result = []
        for log in logs:
            admin = s.query(User).filter(User.id == log.admin_id).first()
            result.append({
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_username": admin.username if admin else "",
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "message": log.message,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            })
        return {"logs": result, "total": total, "page": page, "page_size": page_size}

@router.get("/api/admin/dicts")
async def list_dicts(request: Request, dict_type: str = ""):
    await require_admin(request)
    with Session(engine) as s:
        query = s.query(Dict)
        if dict_type:
            query = query.filter(Dict.type == dict_type)
        dicts = query.order_by(Dict.sort_order).all()
        return {"dicts": [{c.name: getattr(d, c.name) for c in d.__table__.columns} for d in dicts]}

@router.post("/api/admin/dicts")
async def create_dict(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        d = Dict(
            type=data.get("type", ""),
            key=data.get("key", ""),
            value=data.get("value", ""),
            name=data.get("name", ""),
            sort_order=data.get("sort_order", 0),
            is_active=data.get("is_active", True)
        )
        s.add(d)
        s.commit()
        add_admin_log(request, "CREATE", "dict", d.id, f"添加字典：{d.name}")
        return {"id": d.id, "message": "字典已创建"}

@router.put("/api/admin/dicts/{did}")
async def update_dict(did: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        d = s.query(Dict).filter(Dict.id == did).first()
        if not d:
            raise HTTPException(404, "字典不存在")
        for k, v in data.items():
            if hasattr(d, k):
                setattr(d, k, v)
        s.commit()
        add_admin_log(request, "UPDATE", "dict", d.id, f"更新字典：{d.name}")
        return {"message": "字典已更新"}

@router.delete("/api/admin/dicts/{did}")
async def delete_dict(did: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        d = s.query(Dict).filter(Dict.id == did).first()
        if not d:
            raise HTTPException(404, "字典不存在")
        name = d.name
        s.delete(d)
        s.commit()
        add_admin_log(request, "DELETE", "dict", did, f"删除字典：{name}")
        return {"message": "字典已删除"}

@router.get("/api/dicts/{dict_type}")
async def get_dicts_by_type(dict_type: str):
    with Session(engine) as s:
        dicts = s.query(Dict).filter(Dict.type == dict_type, Dict.is_active == True).order_by(Dict.sort_order).all()
        return {"dicts": [{"key": d.key, "value": d.value, "name": d.name} for d in dicts]}
