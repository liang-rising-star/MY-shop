from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import engine
from app.models import CardKey
from app.auth import require_admin

router = APIRouter()

@router.post("/api/admin/cardkeys/import")
async def import_keys(data: dict, request: Request):
    await require_admin(request)
    pid = data["product_id"]
    lines = [l.strip() for l in data["keys"].strip().split("\n") if l.strip()]
    with Session(engine) as s:
        for key in lines:
            s.add(CardKey(product_id=pid, key=key))
        s.commit()
    return {"message": "导入成功", "count": len(lines)}

@router.get("/api/admin/cardkeys")
async def list_keys(request: Request, product_id: int = 0):
    await require_admin(request)
    with Session(engine) as s:
        q = s.query(CardKey)
        if product_id: q = q.filter(CardKey.product_id == product_id)
        keys = q.order_by(CardKey.id.desc()).all()
        return [{c.name: getattr(k, c.name) for c in k.__table__.columns} for k in keys]

@router.delete("/api/admin/cardkeys/{kid}")
async def delete_key(kid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        k = s.query(CardKey).filter(CardKey.id == kid).first()
        if not k:
            raise HTTPException(404, "卡密不存在")
        if k.status == "sold":
            raise HTTPException(400, "已售出的卡密不能删除")
        s.delete(k)
        s.commit()
    return {"message": "已删除"}
