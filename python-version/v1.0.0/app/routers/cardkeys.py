from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import engine
from app.models import CardKey, Product
from app.auth import require_admin

router = APIRouter()

@router.post("/api/admin/cardkeys/import")
async def import_keys(data: dict, request: Request):
    await require_admin(request)
    pid = data["product_id"]
    lines = [l.strip() for l in data["keys"].strip().split("\n") if l.strip()]
    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid).first()
        if not product:
            raise HTTPException(404, "商品不存在")
        
        # 检查总库存限制
        if product.total_stock > 0:
            current_available = s.query(CardKey).filter(
                CardKey.product_id == pid, CardKey.status == "available"
            ).count()
            can_import = product.total_stock - current_available
            if can_import <= 0:
                raise HTTPException(400, f"库存已满，总库存为 {product.total_stock}，当前可用 {current_available}")
            if len(lines) > can_import:
                lines = lines[:can_import]
                msg = f"导入成功，已限制为 {can_import} 条（总库存 {product.total_stock}）"
            else:
                msg = "导入成功"
        else:
            msg = "导入成功"
        
        for key in lines:
            s.add(CardKey(product_id=pid, key=key))
        s.commit()
    return {"message": msg, "count": len(lines)}

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

@router.post("/api/admin/cardkeys/batch-delete")
async def batch_delete_keys(data: dict, request: Request):
    await require_admin(request)
    ids = data.get("ids", [])
    product_id = data.get("product_id")
    count = data.get("count", 0)
    if ids:
        with Session(engine) as s:
            keys = s.query(CardKey).filter(CardKey.id.in_(ids)).all()
            deleted = 0
            skipped = 0
            for k in keys:
                if k.status == "sold":
                    skipped += 1
                else:
                    s.delete(k)
                    deleted += 1
            s.commit()
        return {"message": f"已删除{deleted}条" + (f"，跳过{skipped}条已售出" if skipped else ""), "deleted": deleted, "skipped": skipped}
    elif product_id and count > 0:
        with Session(engine) as s:
            keys = s.query(CardKey).filter(CardKey.product_id == product_id, CardKey.status == "available").limit(count).all()
            deleted = 0
            for k in keys:
                s.delete(k)
                deleted += 1
            s.commit()
        return {"message": f"已删除{deleted}条", "deleted": deleted}
    else:
        raise HTTPException(400, "请选择要删除的卡密")
