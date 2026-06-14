import datetime, random, string
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import engine
from app.models import User, Order, CardKey, RechargeOrder
from app.auth import get_current_user, hash_password, verify_password

router = APIRouter()

RECHARGE_METHODS = [
    {"id": "alipay", "name": "支付宝", "icon": "/static/images/alipay.png"},
    {"id": "wechat", "name": "微信支付", "icon": "/static/images/wx.png"},
    {"id": "qqpay", "name": "QQ支付", "icon": "/static/images/qqpay.png"},
    {"id": "usdt", "name": "USDT", "icon": "/static/images/usdt.png"},
]

def update_user_level(user):
    total = user.points or 0
    if total >= 10000: user.level = 5
    elif total >= 2000: user.level = 4
    elif total >= 500: user.level = 3
    elif total >= 100: user.level = 2
    else: user.level = 1

@router.get("/api/recharge/methods")
async def get_recharge_methods():
    return {"methods": RECHARGE_METHODS}

@router.post("/api/recharge")
async def create_recharge(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    amount = data.get("amount", 0)
    method = data.get("method", "alipay")
    if amount < 1: raise HTTPException(400, "充值金额最少1元")
    
    order_no = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") + str(uid)
    with Session(engine) as s:
        recharge = RechargeOrder(user_id=uid, amount=amount, method=method, order_no=order_no, status="pending")
        s.add(recharge)
        s.commit()
        
        if method == "balance":
            u = s.query(User).filter(User.id == uid).first()
            u.balance = (u.balance or 0) + amount
            recharge.status = "completed"
            recharge.paid_at = datetime.datetime.utcnow()
            s.commit()
            return {"message": "充值成功", "recharge_order_no": order_no, "balance": u.balance}
        
        return {
            "message": "订单已创建，请在支付前确保金额正确",
            "recharge_order_no": order_no,
            "amount": amount,
            "method": method,
            "pay_url": f"/pay/{order_no}",
            "warning": "注意：当前为演示模式，支付未接入真实支付通道"
        }

@router.post("/api/recharge/confirm")
async def confirm_recharge(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    order_no = data.get("order_no", "")
    verify_code = data.get("verify_code", "")
    
    if not order_no:
        raise HTTPException(400, "订单号不能为空")
    
    if len(verify_code) < 6:
        raise HTTPException(400, "请输入正确的验证码进行验证")
    
    with Session(engine) as s:
        recharge = s.query(RechargeOrder).filter(RechargeOrder.order_no == order_no, RechargeOrder.user_id == uid).first()
        if not recharge:
            raise HTTPException(404, "充值订单不存在")
        if recharge.status == "completed":
            raise HTTPException(400, "该订单已处理")
        
        u = s.query(User).filter(User.id == uid).first()
        u.balance = (u.balance or 0) + recharge.amount
        recharge.status = "completed"
        recharge.paid_at = datetime.datetime.utcnow()
        s.commit()
        return {"message": "充值成功", "balance": u.balance}

@router.post("/api/user/upgrade")
async def upgrade_user_level(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    amount = data.get("amount", 0)
    if amount <= 0: raise HTTPException(400, "积分数量无效")
    
    with Session(engine) as s:
        u = s.query(User).filter(User.id == uid).first()
        if (u.points or 0) < amount: raise HTTPException(400, "积分不足")
        
        u.points = (u.points or 0) - amount
        u.total_recharge = (u.total_recharge or 0) + amount
        update_user_level(u)
        s.commit()
        return {"message": "升级成功", "points": u.points, "level": u.level}

@router.get("/api/user/center")
async def user_center(request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    with Session(engine) as s:
        u = s.query(User).filter(User.id == uid).first()
        if not u: raise HTTPException(404)
        order_counts = {}
        for status in ['pending','paid','shipped','completed','refunded']:
            order_counts[status] = s.query(func.count(Order.id)).filter(Order.user_id == uid, Order.status == status).scalar()
        recent = s.query(Order).options(joinedload(Order.product)).filter(
            Order.user_id == uid).order_by(Order.created_at.desc()).limit(5).all()
        return {
            "user": {c.name: getattr(u, c.name) for c in u.__table__.columns if c.name != "password"},
            "order_counts": order_counts,
            "recent_orders": [{
                "id": o.id, "order_no": o.order_no, "product_name": o.product.name if o.product else "",
                "final_price": o.final_price, "status": o.status, "created_at": str(o.created_at),
                "card_keys": [{c.name: getattr(k, c.name) for c in k.__table__.columns} for k in o.card_keys]
            } for o in recent],
        }

@router.get("/api/user/orders")
async def user_orders(request: Request, status: str = "", page: int = 1):
    await get_current_user(request)
    uid = request.state.user_id
    with Session(engine) as s:
        q = s.query(Order).options(joinedload(Order.product), joinedload(Order.card_keys)).filter(Order.user_id == uid)
        if status: q = q.filter(Order.status == status)
        total = q.count()
        orders = q.order_by(Order.created_at.desc()).offset((page-1)*20).limit(20).all()
        return {"total": total, "page": page, "orders": [{
            "id": o.id, "order_no": o.order_no, "product_name": o.product.name if o.product else "",
            "quantity": o.quantity, "total_price": o.total_price, "discount": o.discount,
            "final_price": o.final_price, "status": o.status, "delivery_type": o.delivery_type,
            "created_at": str(o.created_at),
            "card_keys": [{c.name: getattr(k, c.name) for c in k.__table__.columns} for k in o.card_keys]
        } for o in orders]}

@router.put("/api/user/profile")
async def update_profile(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    allowed = ["email", "phone", "real_name", "avatar"]
    with Session(engine) as s:
        u = s.query(User).filter(User.id == uid).first()
        for k, v in data.items():
            if k in allowed: setattr(u, k, v)
        s.commit()
        return {c.name: getattr(u, c.name) for c in u.__table__.columns if c.name != "password"}

@router.post("/api/user/password")
async def change_password(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")
    
    if not old_password or not new_password:
        raise HTTPException(400, "请填写完整信息")
    if len(new_password) < 6:
        raise HTTPException(400, "新密码至少需要6个字符")
    
    with Session(engine) as s:
        u = s.query(User).filter(User.id == uid).first()
        if not verify_password(old_password, u.password):
            raise HTTPException(400, "原密码错误")
        u.password = hash_password(new_password)
        s.commit()
    return {"message": "密码已修改"}

@router.post("/api/user/avatar")
async def upload_avatar(data: dict, request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    with Session(engine) as s:
        s.query(User).filter(User.id == uid).update({"avatar": data["url"]})
        s.commit()
    return {"message": "头像已更新"}

@router.get("/api/user/recharges")
async def get_recharges(request: Request):
    await get_current_user(request)
    uid = request.state.user_id
    with Session(engine) as s:
        recharges = s.query(RechargeOrder).filter(RechargeOrder.user_id == uid).order_by(RechargeOrder.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "order_no": r.order_no,
                "amount": r.amount,
                "status": r.status,
                "created_at": str(r.created_at),
                "paid_at": str(r.paid_at) if r.paid_at else None
            }
            for r in recharges
        ]
