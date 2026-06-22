from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import engine
from app.models import ProductCategory, Product
from app.auth import require_admin

router = APIRouter()

@router.get("/api/categories")
def list_categories():
    with Session(engine) as s:
        cats = s.query(ProductCategory).order_by(ProductCategory.sort_order).all()
        return [{c.name: getattr(cat, c.name) for c in cat.__table__.columns} for cat in cats]

@router.post("/api/admin/categories")
async def create_category(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        cat = ProductCategory(name=data["name"], description=data.get("description",""), sort_order=data.get("sort_order",0))
        s.add(cat); s.commit()
        return {c.name: getattr(cat, c.name) for c in cat.__table__.columns}

@router.delete("/api/admin/categories/{cid}")
async def delete_category(cid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        product_count = s.query(Product).filter(Product.category_id == cid).count()
        if product_count > 0:
            raise HTTPException(400, f"无法删除，该分类下还有 {product_count} 个商品")
        s.query(ProductCategory).filter(ProductCategory.id == cid).delete()
        s.commit()
    return {"message": "已删除"}

@router.put("/api/admin/categories/{cid}")
async def update_category(cid: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        cat = s.query(ProductCategory).filter(ProductCategory.id == cid).first()
        if not cat: raise HTTPException(404, "分类不存在")
        if "name" in data: cat.name = data["name"]
        if "sort_order" in data: cat.sort_order = data["sort_order"]
        s.commit()
        return {c.name: getattr(cat, c.name) for c in cat.__table__.columns}
