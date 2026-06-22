from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import engine
from app.models import MemberLevel
from app.auth import require_admin

router = APIRouter()

@router.get("/api/levels")
def list_levels():
    with Session(engine) as s:
        ls = s.query(MemberLevel).order_by(MemberLevel.level).all()
        return [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in ls]

@router.post("/api/admin/levels")
async def save_level(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        existing = s.query(MemberLevel).filter(MemberLevel.level == data["level"]).first()
        if existing:
            for k, v in data.items():
                if hasattr(existing, k): setattr(existing, k, v)
        else:
            s.add(MemberLevel(**data))
        s.commit()
    return {"message": "已保存"}

@router.delete("/api/admin/levels/{lid}")
async def delete_level(lid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(MemberLevel).filter(MemberLevel.id == lid).delete()
        s.commit()
    return {"message": "已删除"}
