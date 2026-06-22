from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import engine
from app.models import Address
from app.auth import get_current_user, require_admin

router = APIRouter()

@router.get("/api/addresses")
async def list_address(request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    with Session(engine) as s:
        addrs = s.query(Address).filter(Address.user_id == uid).order_by(Address.is_default.desc()).all()
        return [{c.name: getattr(a, c.name) for c in a.__table__.columns} for a in addrs]

@router.post("/api/addresses")
async def save_address(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    with Session(engine) as s:
        if data.get("is_default"):
            s.query(Address).filter(Address.user_id == uid).update({"is_default": False})
        if data.get("id"):
            a = s.query(Address).filter(Address.id == data["id"], Address.user_id == uid).first()
            if not a: raise HTTPException(404)
            for k, v in data.items():
                if hasattr(a, k) and k != "id": setattr(a, k, v)
        else:
            a = Address(user_id=uid, name=data["name"], phone=data["phone"], region=data.get("region",""), detail=data.get("detail",""), is_default=data.get("is_default",False))
            s.add(a)
        s.commit()
        return {c.name: getattr(a, c.name) for c in a.__table__.columns}

@router.delete("/api/addresses/{aid}")
async def delete_address(aid: int, request: Request):
    await get_current_user(request)
    with Session(engine) as s:
        s.query(Address).filter(Address.id == aid, Address.user_id == request.state.user_id).delete()
        s.commit()
    return {"message": "已删除"}
