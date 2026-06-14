import datetime, random, hashlib, hmac, uuid
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models import Product, CardKey, BlindBoxPool, Coupon, Order, User, AppSetting, MemberLevel, Bill, AdminLog, PaymentLog
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
    except Exception as e:
        print(f"[AdminLog Error] {e}")

def get_commission_rate():
    try:
        with Session(engine) as s:
            setting = s.query(AppSetting).filter(AppSetting.key == "config_commission_rate").first()
            return float(setting.value) / 100 if setting else 0.1
    except:
        return 0.1

def get_member_discount(user_id: int, s: Session):
    """获取用户会员折扣"""
    try:
        user = s.query(User).filter(User.id == user_id).first()
        if not user:
            return 1.0
        level = s.query(MemberLevel).filter(MemberLevel.level == user.level).first()
        if not level:
            return 1.0
        return level.discount / 100
    except:
        return 1.0

def get_points_per_yuan():
    """获取每元购买赠送的积分数"""
    try:
        with Session(engine) as s:
            setting = s.query(AppSetting).filter(AppSetting.key == "config_points_per_yuan").first()
            return int(setting.value) if setting else 1
    except:
        return 1

def generate_order_no():
    """生成唯一订单号"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_str = str(uuid.uuid4().hex[:6]).upper()
    return f"ORD{timestamp}{random_str}"

@router.post("/api/orders")
async def create_order(data: dict, request: Request):
    """创建订单 - 先创建pending状态，支付成功后再发货"""
    await get_current_user(request)
    uid = request.state.user_id
    pid = data["product_id"]
    qty = data.get("quantity", 1)
    if qty <= 0: qty = 1

    with Session(engine) as s:
        p = s.query(Product).filter(Product.id == pid).first()
        if not p: raise HTTPException(404, "商品不存在")
        
        if p.type == "blindbox":
            pool = s.query(BlindBoxPool).filter(BlindBoxPool.product_id == pid).all()
            if not pool:
                raise HTTPException(400, "盲盒奖池未配置")
            total_prob = sum(e.probability for e in pool)
            if total_prob > 0 and abs(total_prob - 100) > 0.01:
                raise HTTPException(400, f"奖池概率总和必须为100%，当前为{total_prob}%")
            for entry in pool:
                prize_count = s.query(CardKey).filter(
                    CardKey.product_id == entry.prize_id, 
                    CardKey.status == "available"
                ).count()
                if prize_count == 0:
                    raise HTTPException(400, f"奖品[{entry.prize_id}]库存不足")
        else:
            avail = s.query(CardKey).filter(CardKey.product_id == pid, CardKey.status == "available").count()
            if p.delivery_type == "card_key" and avail < qty:
                raise HTTPException(400, "库存不足")

        total = p.price * qty; discount = 0.0; coupon_id = None
        
        member_discount = get_member_discount(uid, s)
        if member_discount < 1.0:
            discount += total * (1 - member_discount)
        
        if data.get("coupon_code"):
            c = s.query(Coupon).filter(Coupon.code == data["coupon_code"]).with_for_update().first()
            if c:
                if c.expires_at.replace(tzinfo=None) < datetime.datetime.utcnow():
                    raise HTTPException(400, "优惠券已过期")
                if c.max_uses > 0 and c.used_count >= c.max_uses:
                    raise HTTPException(400, "优惠券已被使用完")
                if total < c.min_amount:
                    raise HTTPException(400, f"订单金额需满{c.min_amount}元才可使用此优惠券")
                discount += total * c.value / 100 if c.type == "percentage" else min(c.value, total)
                c.used_count += 1
                coupon_id = c.id

        order_no = generate_order_no()
        order = Order(
            order_no=order_no, 
            user_id=uid, 
            product_id=pid, 
            quantity=qty,
            total_price=total, 
            discount=discount, 
            final_price=total-discount,
            coupon_id=coupon_id, 
            status="pending",
            delivery_type=p.delivery_type
        )
        s.add(order)
        s.flush()
        
        from app import logger
        user = s.query(User).filter(User.id == uid).first()
        username = user.username if user else str(uid)
        logger.log_user_action(username, f"创建订单 {order_no}", f"商品: {p.name}, 金额: ¥{total-discount:.2f}")
        s.add(order)
        s.commit()
        s.refresh(order)

        return {
            "message": "订单创建成功", 
            "order": {c.name:getattr(order,c.name) for c in order.__table__.columns}
        }

@router.post("/api/orders/{oid}/pay")
async def pay_order(oid: int, data: dict, request: Request):
    """订单支付 - 将订单标记为已支付并触发发货"""
    await get_current_user(request)
    uid = request.state.user_id
    
    with Session(engine) as s:
        order = s.query(Order).filter(Order.id == oid, Order.user_id == uid).with_for_update().first()
        if not order:
            raise HTTPException(404, "订单不存在")
        if order.status != "pending":
            raise HTTPException(400, "订单状态不允许支付")
        
        # 检查余额是否足够（示例：余额支付）
        payment_method = data.get("method", "balance")
        if payment_method == "balance":
            user = s.query(User).filter(User.id == uid).with_for_update().first()
            if not user or (user.balance or 0) < order.final_price:
                raise HTTPException(400, "余额不足")
            
            # 扣除余额
            user.balance = (user.balance or 0) - order.final_price
            
            # 添加账单记录
            bill = Bill(
                user_id=uid,
                type="expense",
                category="order_payment",
                amount=order.final_price,
                balance=user.balance,
                message=f"订单支付：{order.order_no}",
                order_no=order.order_no
            )
            s.add(bill)
        
        # 记录支付日志
        payment_log = PaymentLog(
            order_id=order.id,
            order_no=order.order_no,
            user_id=uid,
            amount=order.final_price,
            method=payment_method,
            status="success"
        )
        s.add(payment_log)
        
        # 更新订单状态
        order.status = "paid"
        order.paid_at = datetime.datetime.utcnow()
        s.commit()
        
        # 异步发货（这里同步执行，实际生产可异步）
        try:
            deliver_order(order.id, s)
            s.commit()
        except Exception as e:
            # 发货失败，记录错误但订单状态保持paid
            print(f"[Delivery Error] 订单 {order.order_no} 发货失败: {e}")
            # 可以添加通知或重试机制
        
        return {"message": "支付成功！", "order_id": order.id}

def deliver_order(order_id: int, s: Session):
    """发货逻辑 - 在独立事务中执行"""
    order = s.query(Order).filter(Order.id == order_id).with_for_update().first()
    if not order or order.status != "paid":
        return False
    
    p = s.query(Product).filter(Product.id == order.product_id).first()
    if not p:
        return False
    
    delivered = []
    if p.delivery_type == "card_key":
        if p.type == "blindbox":
            for _ in range(order.quantity):
                prize = pick_prize(s, p.id)
                if not prize: continue
                key = s.query(CardKey).filter(CardKey.product_id==prize.id, CardKey.status=="available").with_for_update().first()
                if not key: continue
                key.status="sold"; key.order_id=order.id; key.sold_at=datetime.datetime.utcnow()
                delivered.append(key)
        else:
            keys = s.query(CardKey).filter(CardKey.product_id==p.id, CardKey.status=="available").with_for_update().limit(order.quantity).all()
            if len(keys) < order.quantity:
                raise Exception("库存不足")
            for k in keys:
                k.status="sold"; k.order_id=order.id; k.sold_at=datetime.datetime.utcnow()
                delivered.append(k)

    # 更新销量和积分
    s.query(Product).filter(Product.id==p.id).update({"total_sold": Product.total_sold + order.quantity})
    points_per_yuan = get_points_per_yuan()
    points_given = int(order.total_price * points_per_yuan)
    s.query(User).filter(User.id==order.user_id).update({"points": User.points + points_given})
    
    # 处理佣金
    inviter = s.query(User).filter(User.id == order.user_id).first()
    if inviter and inviter.invite_uid:
        commission_rate = get_commission_rate()
        commission_amount = (order.total_price - order.discount) * commission_rate
        if commission_amount > 0:
            s.query(User).filter(User.id == inviter.invite_uid).update({
                "commission": User.commission + commission_amount,
                "total_commission": User.total_commission + commission_amount
            })
    
    order.status = "completed"
    return True

@router.post("/api/orders/{oid}/cancel")
async def cancel_order(oid: int, request: Request):
    await get_current_user(request)
    with Session(engine) as s:
        o = s.query(Order).filter(Order.id == oid, Order.user_id == request.state.user_id).with_for_update().first()
        if not o: raise HTTPException(404)
        if o.status not in ["pending"]: 
            raise HTTPException(400, "当前状态不可取消")
        
        # 回滚优惠券
        if o.coupon_id:
            s.query(Coupon).filter(Coupon.id == o.coupon_id).update(
                {"used_count": Coupon.used_count - 1}
            )
        
        o.status = "cancelled"
        s.commit()
    return {"message": "订单已取消"}

@router.post("/api/orders/{oid}/confirm")
async def confirm_order(oid: int, request: Request):
    await get_current_user(request)
    with Session(engine) as s:
        o = s.query(Order).filter(Order.id == oid, Order.user_id == request.state.user_id).first()
        if not o: raise HTTPException(404)
        if o.status != "paid": raise HTTPException(400, "当前状态不可确认收货")
        o.status = "completed"
        s.commit()
    return {"message": "已确认收货"}

def pick_prize(s, pid):
    entries = s.query(BlindBoxPool).filter(BlindBoxPool.product_id==pid).all()
    if not entries: return None
    r = random.random() * 100
    cum = 0
    for e in entries:
        cum += e.probability
        if r < cum:
            prize = s.query(Product).filter(Product.id==e.prize_id).first()
            if prize: return prize
    last_entry = entries[-1]
    return s.query(Product).filter(Product.id==last_entry.prize_id).first()

@router.get("/api/orders")
async def my_orders(request: Request, page: int = 1, page_size: int = 20):
    await get_current_user(request)
    with Session(engine) as s:
        q = s.query(Order).options(joinedload(Order.product), joinedload(Order.card_keys)).filter(
            Order.user_id==request.state.user_id)
        total = q.count()
        orders = q.order_by(Order.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size, "orders": [serialize(o) for o in orders]}

@router.get("/api/admin/orders")
async def admin_orders(request: Request, page: int = 1, page_size: int = 20, status: str = None):
    await require_admin(request)
    with Session(engine) as s:
        q = s.query(Order).options(joinedload(Order.product), joinedload(Order.card_keys))
        if status:
            q = q.filter(Order.status == status)
        total = q.count()
        orders = q.order_by(Order.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"total": total, "page": page, "page_size": page_size, "orders": [serialize(o) for o in orders]}

def serialize(o):
    return {"id":o.id,"order_no":o.order_no,"user_id":o.user_id,"product_id":o.product_id,"quantity":o.quantity,
            "total_price":o.total_price,"discount":o.discount,"final_price":o.final_price,"status":o.status,
            "delivery_type":o.delivery_type,"created_at":str(o.created_at),"paid_at":str(o.paid_at) if o.paid_at else None,
            "product":{c.name:getattr(o.product,c.name) for c in o.product.__table__.columns} if o.product else None,
            "card_keys":[{c.name:getattr(k,c.name) for c in k.__table__.columns} for k in o.card_keys]}

@router.post("/api/admin/orders/{oid}/refund")
async def admin_refund_order(oid: int, data: dict, request: Request):
    """管理员订单退款"""
    await require_admin(request)
    with Session(engine) as s:
        order = s.query(Order).filter(Order.id == oid).with_for_update().first()
        if not order:
            raise HTTPException(404, "订单不存在")
        if order.status not in ["paid", "completed"]:
            raise HTTPException(400, "当前订单状态不可退款")
        
        # 恢复卡密
        if order.delivery_type == "card_key":
            card_keys = s.query(CardKey).filter(CardKey.order_id == oid).all()
            for key in card_keys:
                key.status = "available"
                key.order_id = None
                key.sold_at = None
        
        # 更新订单状态
        order.status = "refunded"
        
        # 退还用户余额
        user = s.query(User).filter(User.id == order.user_id).first()
        if user:
            user.balance = (user.balance or 0) + order.final_price
            
            # 添加账单记录
            bill = Bill(
                user_id=user.id,
                type="income",
                category="refund",
                amount=order.final_price,
                balance=user.balance,
                message=f"订单退款：{order.order_no}",
                order_no=order.order_no
            )
            s.add(bill)
        
        # 回滚销量
        s.query(Product).filter(Product.id == order.product_id).update(
            {"total_sold": Product.total_sold - order.quantity}
        )
        
        # 回滚优惠券
        if order.coupon_id:
            s.query(Coupon).filter(Coupon.id == order.coupon_id).update(
                {"used_count": Coupon.used_count - 1}
            )
        
        s.commit()
        
        add_admin_log(
            request, "REFUND", "order", order.id,
            f"退款订单 {order.order_no}，金额 {order.final_price} 元"
        )
        
        return {"message": "退款成功"}

@router.post("/api/admin/orders/{oid}/complete")
async def admin_complete_order(oid: int, request: Request):
    """管理员手动完成订单"""
    await require_admin(request)
    with Session(engine) as s:
        order = s.query(Order).filter(Order.id == oid).first()
        if not order:
            raise HTTPException(404, "订单不存在")
        if order.status not in ["paid", "pending"]:
            raise HTTPException(400, "当前订单状态不可完成")
        order.status = "completed"
        s.commit()
        return {"message": "订单已完成"}

@router.post("/api/admin/orders/{oid}/status")
async def admin_update_order_status(oid: int, data: dict, request: Request):
    """管理员更新订单状态 - 安全版本"""
    await require_admin(request)
    new_status = data.get("status")
    if new_status not in ["pending", "paid", "completed", "cancelled", "refunded"]:
        raise HTTPException(400, "无效的订单状态")
    
    with Session(engine) as s:
        order = s.query(Order).filter(Order.id == oid).with_for_update().first()
        if not order:
            raise HTTPException(404, "订单不存在")
        
        old_status = order.status
        
        # 如果从pending变为paid，需要执行发货
        if old_status == "pending" and new_status == "paid":
            order.paid_at = datetime.datetime.utcnow()
            order.status = new_status
            try:
                deliver_order(order.id, s)
            except Exception as e:
                print(f"[Manual Delivery Error] {e}")
        else:
            order.status = new_status
        
        s.commit()
        
        add_admin_log(
            request, "UPDATE", "order", order.id,
            f"订单 {order.order_no} 状态从 {old_status} 变更为 {new_status}"
        )
        
        return {"message": "订单状态已更新"}

@router.post("/api/admin/orders/{oid}/redeliver")
async def admin_redeliver_order(oid: int, request: Request):
    """管理员手动重新发货 - 用于发货失败的情况"""
    await require_admin(request)
    
    with Session(engine) as s:
        order = s.query(Order).filter(Order.id == oid).with_for_update().first()
        if not order:
            raise HTTPException(404, "订单不存在")
        if order.status not in ["paid", "completed"]:
            raise HTTPException(400, "只有已支付的订单才能重新发货")
        
        # 检查是否已经发货过
        existing_keys = s.query(CardKey).filter(CardKey.order_id == oid).count()
        if existing_keys > 0:
            raise HTTPException(400, "该订单已经发货过")
        
        try:
            deliver_order(order.id, s)
            s.commit()
            
            add_admin_log(
                request, "REDELIVER", "order", order.id,
                f"重新发货订单 {order.order_no}"
            )
            
            return {"message": "重新发货成功"}
        except Exception as e:
            s.rollback()
            raise HTTPException(500, f"发货失败: {str(e)}")
