"""
抽奖系统路由
"""
import random, json, datetime, asyncio
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import engine
from app.models import User, Product, Coupon, CardKey, Order, AppSetting, LotteryWheel, LotteryPrize, LotteryTicket
from app.auth import get_current_user
from app.utils.concurrency import concurrency_handler

router = APIRouter()

def get_user_tickets(user_id: int, wheel_id: int = None):
    """获取用户可用抽奖券数量"""
    with Session(engine) as s:
        query = s.query(LotteryTicket).filter(
            LotteryTicket.user_id == user_id,
            LotteryTicket.status == "active"
        )
        if wheel_id:
            query = query.filter(
                (LotteryTicket.wheel_id == wheel_id) | 
                (LotteryTicket.wheel_id == None)
            )
        return query.count()

def get_daily_free_count(user_id: int, wheel_id: int) -> int:
    """获取今日免费次数"""
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    with Session(engine) as s:
        count = s.query(LotteryTicket).filter(
            LotteryTicket.user_id == user_id,
            LotteryTicket.wheel_id == wheel_id,
            LotteryTicket.source == "free",
            LotteryTicket.created_at >= today_start
        ).count()
        return count

def get_daily_count(user_id: int, wheel_id: int) -> int:
    """获取今日抽奖次数"""
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    with Session(engine) as s:
        from app.models import LotteryRecord
        count = s.query(LotteryRecord).filter(
            LotteryRecord.user_id == user_id,
            LotteryRecord.product_id == wheel_id,
            LotteryRecord.created_at >= today_start
        ).count()
        return count

def check_user_points(user_id: int, required: int) -> bool:
    """检查用户积分是否足够"""
    with Session(engine) as s:
        user = s.query(User).filter(User.id == user_id).first()
        return user and (user.points or 0) >= required

def deduct_points(user_id: int, points: int):
    """扣除用户积分"""
    with Session(engine) as s:
        s.query(User).filter(User.id == user_id).update(
            {"points": User.points - points}
        )
        s.commit()

async def lottery_draw(user_id: int, wheel_id: int, cost_type: str, cost_value: int, 
                      ip_address: str = "") -> dict:
    """抽奖核心逻辑"""
    with Session(engine) as s:
        # 获取转盘信息
        wheel = s.query(LotteryWheel).filter(LotteryWheel.id == wheel_id).first()
        if not wheel or not wheel.is_active:
            raise HTTPException(400, "转盘不存在或已禁用")
        
        # 获取所有奖品
        prizes = s.query(LotteryPrize).filter(
            LotteryPrize.wheel_id == wheel_id
        ).all()
        
        if not prizes:
            raise HTTPException(400, "奖品未配置")
        
        # 扣除成本
        if cost_type == "points":
            deduct_points(user_id, cost_value)
        elif cost_type == "ticket":
            ticket = s.query(LotteryTicket).filter(
                LotteryTicket.user_id == user_id,
                LotteryTicket.status == "active",
                LotteryTicket.wheel_id.in_([wheel_id, None])
            ).order_by(LotteryTicket.created_at).first()
            if not ticket:
                raise HTTPException(400, "抽奖券不足")
            ticket.status = "used"
            ticket.used_at = datetime.datetime.utcnow()
        
        # 根据概率抽奖
        prize = pick_prize(prizes, s)
        
        # 记录抽奖
        from app.models import LotteryRecord
        record = LotteryRecord(
            user_id=user_id,
            product_id=wheel_id,
            prize_name=prize.name,
            prize_type=prize.prize_type,
            cost_points=cost_value,
            ip_address=ip_address,
            is_winner=not prize.is_default
        )
        s.add(record)
        
        # 发放奖品
        prize_info = await deliver_prize(user_id, prize, s)
        
        s.commit()
        
        return {
            "record_id": record.id,
            "prize": prize_info,
            "is_winner": record.is_winner
        }

def pick_prize(prizes: list, s: Session) -> LotteryPrize:
    """根据概率抽取奖品"""
    # 先过滤有库存的奖品
    available_prizes = []
    for p in prizes:
        if p.stock == -1 or p.stock > 0:
            available_prizes.append(p)
    
    if not available_prizes:
        # 所有奖品都没库存，返回默认奖品
        for p in prizes:
            if p.is_default:
                return p
        return prizes[0]
    
    # 概率抽奖
    total_prob = sum(p.probability for p in available_prizes)
    if total_prob == 0:
        return random.choice(available_prizes)
    
    r = random.random() * total_prob
    cum = 0
    for prize in available_prizes:
        cum += prize.probability
        if r <= cum:
            # 扣减库存
            if prize.stock > 0:
                prize.stock -= 1
            return prize
    
    # 默认返回最后一个
    return available_prizes[-1]

async def deliver_prize(user_id: int, prize: LotteryPrize, s: Session) -> dict:
    """发放奖品"""
    prize_info = {
        "id": prize.id,
        "name": prize.name,
        "type": prize.prize_type,
        "value": prize.prize_value,
        "description": ""
    }
    
    if prize.prize_type == "coupon":
        # 发放优惠券
        coupon_id = int(prize.prize_value)
        coupon = s.query(Coupon).filter(Coupon.id == coupon_id).first()
        if coupon:
            from app.models import UserCoupon
            user_coupon = UserCoupon(
                user_id=user_id,
                coupon_id=coupon_id
            )
            s.add(user_coupon)
            prize_info["description"] = f"获得优惠券：{coupon.name}"
    
    elif prize.prize_type == "ticket":
        # 发放抽奖券
        for i in range(int(prize.prize_value)):
            ticket = LotteryTicket(
                code=f"LT{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}",
                user_id=user_id,
                wheel_id=prize.wheel_id,
                source="lottery",
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=30)
            )
            s.add(ticket)
        prize_info["description"] = f"获得{int(prize.prize_value)}张抽奖券"
    
    elif prize.prize_type == "points":
        # 发放积分
        points = int(prize.prize_value)
        user = s.query(User).filter(User.id == user_id).first()
        if user:
            user.points = (user.points or 0) + points
        prize_info["description"] = f"获得{points}积分"
    
    elif prize.prize_type == "product":
        # 发放商品（卡密）
        try:
            product_data = json.loads(prize.prize_value)
            product_id = product_data.get("product_id")
            quantity = product_data.get("quantity", 1)
            
            product = s.query(Product).filter(Product.id == product_id).first()
            if product:
                card_keys = s.query(CardKey).filter(
                    CardKey.product_id == product_id,
                    CardKey.status == "available"
                ).limit(quantity).all()
                
                delivered = []
                for k in card_keys:
                    k.status = "sold"
                    k.order_id = 0
                    k.sold_at = datetime.datetime.utcnow()
                    delivered.append(k.key)
                
                prize_info["description"] = f"获得商品：{product.name}"
                prize_info["card_keys"] = delivered
        except:
            prize_info["description"] = "获得商品奖励"
    
    return prize_info

@router.get("/api/lottery/wheels")
async def get_wheels(request: Request):
    """获取所有可用转盘"""
    with Session(engine) as s:
        wheels = s.query(LotteryWheel).filter(
            LotteryWheel.is_active == True
        ).order_by(LotteryWheel.sort_order).all()
        
        result = []
        for w in wheels:
            prizes = s.query(LotteryPrize).filter(
                LotteryPrize.wheel_id == w.id
            ).order_by(LotteryPrize.sort_order).all()
            
            result.append({
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "image_url": w.image_url,
                "price_type": w.price_type,
                "price_value": w.price_value,
                "free_daily": w.free_daily,
                "min_points": w.min_points,
                "max_daily": w.max_daily,
                "prizes": [{
                    "id": p.id,
                    "name": p.name,
                    "type": p.prize_type,
                    "value": p.prize_value,
                    "probability": p.probability,
                    "image_url": p.image_url,
                    "is_default": p.is_default
                } for p in prizes]
            })
        
        return {"wheels": result}

@router.post("/api/lottery/draw")
async def draw_lottery(request: Request, data: dict):
    """抽奖"""
    try:
        user = await get_current_user(request)
        user_id = user["id"]
        wheel_id = data.get("wheel_id")
        draw_type = data.get("type", "auto")
        
        with Session(engine) as s:
            wheel = s.query(LotteryWheel).filter(LotteryWheel.id == wheel_id).first()
            if not wheel:
                raise HTTPException(400, "转盘不存在")
            
            # 检查限流
            if not await concurrency_handler.check_rate_limit(
                user_id, f"lottery_{wheel_id}", 
                max_requests=wheel.max_daily if wheel.max_daily > 0 else 100,
                window=86400
            ):
                raise HTTPException(400, "今日抽奖次数已达上限")
            
            # 确定扣费方式
            cost_type = "points"
            cost_value = wheel.price_value
            
            # 检查免费次数
            if draw_type == "free" or (draw_type == "auto" and wheel.free_daily > 0):
                free_used = get_daily_free_count(user_id, wheel_id)
                if free_used < wheel.free_daily:
                    cost_type = "free"
                    cost_value = 0
                elif draw_type == "free":
                    raise HTTPException(400, "今日免费次数已用完")
            
            # 检查抽奖券
            if cost_type == "points" and draw_type in ["ticket", "auto"]:
                tickets = get_user_tickets(user_id, wheel_id)
                if tickets > 0:
                    cost_type = "ticket"
                    cost_value = 1
                elif draw_type == "ticket":
                    raise HTTPException(400, "抽奖券不足")
            
            # 检查积分
            if cost_type == "points":
                if not check_user_points(user_id, wheel.price_value):
                    raise HTTPException(400, "积分不足")
                if wheel.price_type == "ticket":
                    raise HTTPException(400, "需要使用抽奖券")
            
            # 执行抽奖
            ip = request.client.host if request.client else ""
            result = await lottery_draw(user_id, wheel_id, cost_type, cost_value, ip)
            
            return {
                "success": True,
                **result,
                "cost_type": cost_type,
                "cost_value": cost_value
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Lottery Error] {e}")
        raise HTTPException(500, "抽奖失败")

@router.get("/api/lottery/records")
async def get_lottery_records(request: Request, page: int = 1, page_size: int = 20):
    """获取抽奖记录"""
    user = await get_current_user(request)
    with Session(engine) as s:
        from app.models import LotteryRecord
        query = s.query(LotteryRecord).filter(
            LotteryRecord.user_id == user["id"]
        ).order_by(LotteryRecord.created_at.desc())
        
        total = query.count()
        records = query.offset((page-1)*page_size).limit(page_size).all()
        
        return {
            "total": total,
            "records": [{
                "id": r.id,
                "wheel_id": r.product_id,
                "prize_name": r.prize_name,
                "cost_type": "points",
                "cost_value": r.cost_points,
                "is_winner": r.is_winner,
                "status": "completed",
                "created_at": str(r.created_at)
            } for r in records]
        }

@router.get("/api/lottery/tickets")
async def get_tickets(request: Request):
    """获取用户抽奖券"""
    user = await get_current_user(request)
    with Session(engine) as s:
        tickets = s.query(LotteryTicket).filter(
            LotteryTicket.user_id == user["id"],
            LotteryTicket.status == "active"
        ).all()
        
        return {
            "count": len(tickets),
            "tickets": [{
                "id": t.id,
                "code": t.code,
                "wheel_id": t.wheel_id,
                "expires_at": str(t.expires_at) if t.expires_at else None,
                "created_at": str(t.created_at)
            } for t in tickets]
        }

@router.get("/api/lottery/wheels/admin")
async def admin_get_wheels(request: Request):
    """管理员获取所有转盘"""
    await get_current_user(request, require_admin=True)
    with Session(engine) as s:
        wheels = s.query(LotteryWheel).order_by(LotteryWheel.sort_order).all()
        result = []
        for w in wheels:
            prizes = s.query(LotteryPrize).filter(
                LotteryPrize.wheel_id == w.id
            ).order_by(LotteryPrize.sort_order).all()
            
            result.append({
                **{
                    c.name: getattr(w, c.name) for c in w.__table__.columns
                },
                "prizes": [{
                    **{
                        c.name: getattr(p, c.name) for c in p.__table__.columns
                    }
                } for p in prizes]
            })
        return {"wheels": result}

@router.post("/api/admin/lottery/wheels")
async def admin_create_wheel(request: Request, data: dict):
    """管理员创建转盘"""
    await get_current_user(request, require_admin=True)
    with Session(engine) as s:
        wheel = LotteryWheel(
            name=data.get("name", "新转盘"),
            description=data.get("description", ""),
            image_url=data.get("image_url", ""),
            price_type=data.get("price_type", "points"),
            price_value=data.get("price_value", 10),
            free_daily=data.get("free_daily", 0),
            min_points=data.get("min_points", 0),
            max_daily=data.get("max_daily", 0),
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0)
        )
        s.add(wheel)
        s.commit()
        s.refresh(wheel)
        return {"success": True, "id": wheel.id}

@router.put("/api/admin/lottery/wheels/{wheel_id}")
async def admin_update_wheel(wheel_id: int, request: Request, data: dict):
    """管理员更新转盘"""
    await get_current_user(request, require_admin=True)
    with Session(engine) as s:
        wheel = s.query(LotteryWheel).filter(LotteryWheel.id == wheel_id).first()
        if not wheel:
            raise HTTPException(404, "转盘不存在")
        
        for key, value in data.items():
            if hasattr(wheel, key):
                setattr(wheel, key, value)
        
        s.commit()
        return {"success": True}

@router.post("/api/admin/lottery/prizes")
async def admin_create_prize(request: Request, data: dict):
    """管理员添加奖品"""
    await get_current_user(request, require_admin=True)
    with Session(engine) as s:
        prize = LotteryPrize(
            wheel_id=data.get("wheel_id"),
            name=data.get("name", ""),
            prize_type=data.get("prize_type", "points"),
            prize_value=str(data.get("prize_value", "")),
            probability=data.get("probability", 0),
            is_default=data.get("is_default", False),
            stock=data.get("stock", -1),
            total_stock=data.get("total_stock", 0),
            sort_order=data.get("sort_order", 0),
            image_url=data.get("image_url", "")
        )
        s.add(prize)
        s.commit()
        s.refresh(prize)
        return {"success": True, "id": prize.id}

@router.put("/api/admin/lottery/prizes/{prize_id}")
async def admin_update_prize(prize_id: int, request: Request, data: dict):
    """管理员更新奖品"""
    await get_current_user(request, require_admin=True)
    with Session(engine) as s:
        prize = s.query(LotteryPrize).filter(LotteryPrize.id == prize_id).first()
        if not prize:
            raise HTTPException(404, "奖品不存在")
        
        for key, value in data.items():
            if hasattr(prize, key):
                setattr(prize, key, value)
        
        s.commit()
        return {"success": True}

@router.delete("/api/admin/lottery/wheels/{wheel_id}")
async def admin_delete_wheel(wheel_id: int, request: Request):
    """管理员删除转盘"""
    await get_current_user(request, require_admin=True)
    with Session(engine) as s:
        # 删除关联奖品
        s.query(LotteryPrize).filter(LotteryPrize.wheel_id == wheel_id).delete()
        # 删除转盘
        s.query(LotteryWheel).filter(LotteryWheel.id == wheel_id).delete()
        s.commit()
        return {"success": True}
