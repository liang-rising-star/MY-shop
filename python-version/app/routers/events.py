from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import engine
from app.models import Product, AppSetting, CardKey
from app.auth import require_admin, get_current_user
from app.config import config
import os
import json
import datetime

router = APIRouter()


def get_event_settings():
    """获取活动设置"""
    with Session(engine) as s:
        rows = s.query(AppSetting).filter(AppSetting.key.like("event_%")).all()
        event = {}
        for r in rows:
            key = r.key.replace("event_", "")
            try:
                if r.value == "True":
                    event[key] = True
                elif r.value == "False":
                    event[key] = False
                elif r.value.isdigit():
                    event[key] = int(r.value)
                elif r.value.startswith("["):
                    event[key] = json.loads(r.value.replace("'", '"'))
                else:
                    event[key] = r.value
            except:
                event[key] = r.value
        return event


@router.get("/api/admin/events")
async def get_admin_events(request: Request):
    """获取活动设置和活动商品列表"""
    await require_admin(request)
    settings = get_event_settings()

    with Session(engine) as s:
        products = s.query(Product).filter(Product.type == "timed").order_by(Product.sort_order).all()

        product_list = []
        for p in products:
            available_count = s.query(CardKey).filter(
                CardKey.product_id == p.id,
                CardKey.status == "available"
            ).count()

            product_list.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "original_price": p.original_price,
                "discount_price": p.discount_price,
                "stock": p.stock,
                "card_key_count": available_count,
                "start_at": p.start_at.isoformat() if p.start_at else None,
                "end_at": p.end_at.isoformat() if p.end_at else None,
                "is_active": p.is_active,
                "sort_order": p.sort_order,
                "image_url": p.image_url
            })

        return {
            "settings": settings,
            "products": product_list
        }


@router.get("/api/admin/event")
async def get_event(request: Request):
    """获取活动设置 - 兼容旧接口"""
    await require_admin(request)
    event = get_event_settings()
    return {"event": event}


@router.post("/api/admin/event")
async def save_event(data: dict, request: Request):
    """保存活动设置 - 兼容旧接口"""
    await require_admin(request)

    with Session(engine) as s:
        for k, v in data.items():
            key = f"event_{k}"
            if isinstance(v, (list, dict)):
                val = json.dumps(v)
            elif v is True:
                val = "True"
            elif v is False:
                val = "False"
            else:
                val = str(v)
            existing = s.query(AppSetting).filter(AppSetting.key == key).first()
            if existing:
                existing.value = val
            else:
                s.add(AppSetting(key=key, value=val))
        s.commit()

    return {"message": "活动设置已保存"}


@router.get("/api/events")
async def get_events(request: Request):
    """前台获取活动信息"""
    try:
        user = await get_current_user(request)
    except:
        raise HTTPException(status_code=401, detail="请先登录")

    settings = get_event_settings()

    with Session(engine) as s:
        now = datetime.datetime.utcnow()
        products = s.query(Product).filter(
            Product.type == "timed",
            Product.is_active == True
        ).order_by(Product.sort_order).all()

        product_list = []
        for p in products:
            available_count = s.query(CardKey).filter(
                CardKey.product_id == p.id,
                CardKey.status == "available"
            ).count()

            product_data = {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "original_price": p.original_price,
                "discount_price": p.discount_price,
                "total_sold": p.total_sold,
                "card_key_count": available_count,
                "start_at": p.start_at.isoformat() if p.start_at else None,
                "end_at": p.end_at.isoformat() if p.end_at else None,
                "image_url": p.image_url,
                "category": {"id": p.category.id, "name": p.category.name} if p.category else None
            }

            if p.start_at and p.end_at:
                if p.start_at <= now <= p.end_at:
                    product_list.append(product_data)
            elif p.end_at:
                if now <= p.end_at:
                    product_list.append(product_data)
            else:
                product_list.append(product_data)

        return {
            "settings": settings,
            "products": product_list
        }


@router.post("/api/admin/events/products")
async def create_event_product(data: dict, request: Request):
    """创建活动商品"""
    await require_admin(request)

    with Session(engine) as s:
        product = Product(
            name=data.get("name", ""),
            description=data.get("description", ""),
            price=data.get("price", 0),
            original_price=data.get("original_price"),
            discount_price=data.get("discount_price"),
            type="timed",
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0),
            start_at=datetime.datetime.fromisoformat(data["start_at"]) if data.get("start_at") else None,
            end_at=datetime.datetime.fromisoformat(data["end_at"]) if data.get("end_at") else None,
            image_url=data.get("image_url", ""),
            stock=data.get("stock", -1)
        )
        s.add(product)
        s.commit()

        return {"id": product.id, "message": "活动商品创建成功"}


@router.put("/api/admin/events/products/{pid}")
async def update_event_product(pid: int, data: dict, request: Request):
    """更新活动商品"""
    await require_admin(request)

    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid, Product.type == "timed").first()
        if not product:
            raise HTTPException(status_code=404, detail="活动商品不存在")

        for key, value in data.items():
            if hasattr(product, key) and key not in ["id", "created_at", "category"]:
                if key in ["start_at", "end_at"]:
                    value = datetime.datetime.fromisoformat(value) if value else None
                setattr(product, key, value)

        s.commit()

        return {"message": "活动商品更新成功"}


@router.delete("/api/admin/events/products/{pid}")
async def delete_event_product(pid: int, request: Request):
    """删除活动商品（改为普通商品）"""
    await require_admin(request)

    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid, Product.type == "timed").first()
        if not product:
            raise HTTPException(status_code=404, detail="活动商品不存在")

        product.type = "normal"
        product.start_at = None
        product.end_at = None
        s.commit()

        return {"message": "活动商品已取消"}


@router.get("/api/events/check-participation")
async def check_event_participation(request: Request):
    """检查用户参与活动的情况"""
    try:
        user = await get_current_user(request)
    except:
        raise HTTPException(status_code=401, detail="请先登录")

    with Session(engine) as s:
        from app.models import Order
        orders = s.query(Order).filter(
            Order.user_id == user.id,
            Order.status.in_(["paid", "completed"])
        ).all()

        event_product_ids = []
        for o in orders:
            p = s.query(Product).filter(Product.id == o.product_id, Product.type == "timed").first()
            if p:
                event_product_ids.append(o.product_id)

        return {
            "participated_events": event_product_ids,
            "participation_count": len(event_product_ids)
        }
