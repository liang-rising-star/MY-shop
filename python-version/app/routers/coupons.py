import datetime
import json
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from app.database import engine
from app.models import Coupon, UserCoupon, PromoCode, User, InviteRecord, CouponRule
from app.auth import get_current_user, require_admin

router = APIRouter()

def _field(data, *names):
    for n in names:
        if n in data:
            return data[n]
    return None

@router.post("/api/admin/coupons")
async def create_coupon(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        expires_at = _field(data, "expires_at", "ExpiresAt")
        if expires_at:
            expires_at = datetime.datetime.fromisoformat(expires_at.replace("Z","+00:00"))
        c = Coupon(
            name=_field(data, "name", "Code", "code") or "",
            type=_field(data, "type", "Type") or "percentage",
            value=_field(data, "value", "Value") or 0,
            min_amount=_field(data, "min_amount", "MinAmount") or 0,
            total_count=_field(data, "total_count", "TotalCount") or 0,
            max_uses=_field(data, "max_uses", "MaxUses") or 0,
            expires_at=expires_at
        )
        s.add(c)
        s.commit()
        return {
            "id": c.id,
            "name": c.name,
            "Code": c.name,
            "type": c.type,
            "Type": c.type,
            "value": c.value,
            "Value": c.value,
            "min_amount": c.min_amount,
            "total_count": c.total_count,
            "issued_count": 0,
            "max_uses": c.max_uses,
            "MaxUses": c.max_uses,
            "used_count": c.used_count,
            "UsedCount": c.used_count,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None
        }

@router.get("/api/admin/coupons")
async def list_coupons(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        cs = s.query(Coupon).order_by(Coupon.created_at.desc()).all()
        result = []
        for c in cs:
            issued_count = s.query(UserCoupon).filter(UserCoupon.coupon_id == c.id).count()
            result.append({
                "id": c.id,
                "ID": c.id,
                "name": c.name,
                "Code": c.name,
                "type": c.type,
                "Type": c.type,
                "value": c.value,
                "Value": c.value,
                "min_amount": c.min_amount,
                "MinAmount": c.min_amount,
                "total_count": c.total_count,
                "TotalCount": c.total_count,
                "issued_count": issued_count,
                "max_uses": c.max_uses,
                "MaxUses": c.max_uses,
                "used_count": c.used_count,
                "UsedCount": c.used_count,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                "ExpiresAt": c.expires_at.isoformat() if c.expires_at else None
            })
        return result

@router.delete("/api/admin/coupons/{cid}")
async def delete_coupon(cid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(Coupon).filter(Coupon.id == cid).delete()
        s.query(UserCoupon).filter(UserCoupon.coupon_id == cid).delete()
        s.commit()
    return {"message": "已删除"}

@router.post("/api/admin/coupons/{cid}/give")
async def give_coupon_to_user(cid: int, data: dict, request: Request):
    await require_admin(request)
    username = data.get("username", "")
    if not username:
        raise HTTPException(400, "请提供用户名")
    
    with Session(engine) as s:
        user = s.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(404, "用户不存在")
        
        coupon = s.query(Coupon).filter(Coupon.id == cid).first()
        if not coupon:
            raise HTTPException(404, "优惠券不存在")
        
        if coupon.expires_at and coupon.expires_at < datetime.datetime.utcnow():
            raise HTTPException(400, "优惠券已过期")
        
        if coupon.total_count > 0:
            issued_count = s.query(UserCoupon).filter(UserCoupon.coupon_id == cid).count()
            if issued_count >= coupon.total_count:
                raise HTTPException(400, "优惠券已发完")
        
        existing = s.query(UserCoupon).filter(
            UserCoupon.user_id == user.id,
            UserCoupon.coupon_id == cid
        ).first()
        if existing:
            raise HTTPException(400, f"用户 {username} 已拥有此优惠券")
        
        uc = UserCoupon(user_id=user.id, coupon_id=cid)
        s.add(uc)
        s.commit()
        return {"message": f"已发放给 {username}"}

@router.post("/api/coupon/claim")
async def claim_coupon(data: dict, request: Request):
    await get_current_user(request)
    with Session(engine) as s:
        c = s.query(Coupon).filter(Coupon.name == data["code"]).first()
        if not c:
            raise HTTPException(404, "优惠码不存在")
        if s.query(UserCoupon).filter(UserCoupon.user_id==request.state.user_id, UserCoupon.coupon_id==c.id).first():
            raise HTTPException(400, "已领取过")
        s.add(UserCoupon(user_id=request.state.user_id, coupon_id=c.id))
        s.commit()
    return {"message": "领取成功"}

@router.get("/api/coupons/mine")
async def my_coupons(request: Request):
    await get_current_user(request)
    with Session(engine) as s:
        ucs = s.query(UserCoupon).options(joinedload(UserCoupon.coupon)).filter(
            UserCoupon.user_id==request.state.user_id, UserCoupon.used_at==None
        ).all()
        result = []
        for uc in ucs:
            if uc.coupon:
                if uc.coupon.expires_at and uc.coupon.expires_at < datetime.datetime.utcnow():
                    continue
                result.append({
                    "id": uc.id,
                    "coupon_id": uc.coupon_id,
                    "created_at": uc.created_at.isoformat() if uc.created_at else None,
                    "coupon": {
                        "id": uc.coupon.id,
                        "name": uc.coupon.name,
                        "type": uc.coupon.type,
                        "value": uc.coupon.value,
                        "min_amount": uc.coupon.min_amount,
                        "expires_at": uc.coupon.expires_at.isoformat() if uc.coupon.expires_at else None
                    }
                })
        return result

@router.get("/api/admin/promo-codes")
async def list_promo_codes(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        pcs = s.query(PromoCode).order_by(PromoCode.created_at.desc()).all()
        result = []
        for pc in pcs:
            result.append({
                "id": pc.id,
                "code": pc.code,
                "type": pc.type,
                "value": pc.value,
                "min_amount": pc.min_amount,
                "coupon_id": pc.coupon_id,
                "give_count": pc.give_count,
                "remark": pc.remark,
                "max_uses": pc.max_uses,
                "used_count": pc.used_count,
                "expires_at": pc.expires_at.isoformat() if pc.expires_at else None
            })
        return result

@router.post("/api/admin/promo-codes")
async def create_promo_code(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        pc = PromoCode(
            code=data["code"],
            type=data.get("type"),
            value=data.get("value", 0),
            min_amount=data.get("min_amount", 0),
            coupon_id=data.get("coupon_id"),
            give_count=data.get("give_count", 1),
            remark=data.get("remark", ""),
            max_uses=data.get("max_uses", 0),
            expires_at=datetime.datetime.fromisoformat(data["expires_at"].replace("Z","+00:00")) if data.get("expires_at") else None
        )
        s.add(pc)
        s.commit()
        return {
            "id": pc.id,
            "code": pc.code,
            "type": pc.type,
            "value": pc.value,
            "coupon_id": pc.coupon_id,
            "max_uses": pc.max_uses,
            "used_count": pc.used_count,
            "expires_at": pc.expires_at.isoformat() if pc.expires_at else None
        }

@router.delete("/api/admin/promo-codes/{pid}")
async def delete_promo_code(pid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(PromoCode).filter(PromoCode.id == pid).delete()
        s.commit()
    return {"message": "已删除"}

@router.post("/api/promo-code/use")
async def use_promo_code(data: dict, request: Request):
    user = await get_current_user(request)
    code = data.get("code", "").strip()
    if not code:
        raise HTTPException(400, "请输入优惠码")
    
    with Session(engine) as s:
        pc = s.query(PromoCode).filter(PromoCode.code == code.upper()).first()
        if not pc:
            raise HTTPException(404, "优惠码不存在")
        
        if pc.expires_at and pc.expires_at < datetime.datetime.utcnow():
            raise HTTPException(400, "优惠码已过期")
        
        if pc.max_uses > 0 and pc.used_count >= pc.max_uses:
            raise HTTPException(400, "优惠码已用完")
        
        if pc.coupon_id:
            # 兑换码：获取优惠券
            coupon = s.query(Coupon).filter(Coupon.id == pc.coupon_id).first()
            if not coupon:
                raise HTTPException(404, "关联的优惠券不存在")
            
            if coupon.expires_at and coupon.expires_at < datetime.datetime.utcnow():
                raise HTTPException(400, "关联的优惠券已过期")
            
            # 检查用户是否已拥有此优惠券
            existing = s.query(UserCoupon).filter(
                UserCoupon.user_id == user["id"],
                UserCoupon.coupon_id == coupon.id
            ).first()
            if existing:
                raise HTTPException(400, "您已拥有此优惠券")
            
            # 发放多张优惠券
            for _ in range(pc.give_count or 1):
                uc = UserCoupon(user_id=user["id"], coupon_id=coupon.id)
                s.add(uc)
            
            pc.used_count += 1
            s.commit()
            return {"message": f"成功获得优惠券！", "coupon_name": coupon.name}
        elif pc.type:
            # 购物优惠：这里目前不做实际操作，返回优惠信息
            pc.used_count += 1
            s.commit()
            return {
                "message": "优惠码已使用！",
                "discount": pc.value,
                "type": pc.type,
                "min_amount": pc.min_amount
            }
        else:
            raise HTTPException(400, "无效的优惠码")

# 邀请码相关API
@router.get("/api/admin/invites/settings")
async def get_invite_settings(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        from app.models import AppSetting
        settings = {}
        for key in ["reward_new_user", "reward_inviter", "reward_coupon", "reward_coupon_count"]:
            row = s.query(AppSetting).filter(AppSetting.key == f"invite_{key}").first()
            if row:
                settings[key] = int(row.value) if key in ["reward_new_user", "reward_inviter", "reward_coupon_count"] else row.value
        return {"settings": settings}

@router.post("/api/admin/invites/settings")
async def save_invite_settings(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        from app.models import AppSetting
        for key, value in data.items():
            db_key = f"invite_{key}"
            existing = s.query(AppSetting).filter(AppSetting.key == db_key).first()
            if existing:
                existing.value = str(value)
            else:
                s.add(AppSetting(key=db_key, value=str(value)))
        s.commit()
        return {"message": "设置已保存"}

@router.get("/api/admin/invites/records")
async def get_invite_records(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        records = s.query(InviteRecord).order_by(InviteRecord.created_at.desc()).all()
        result = []
        for r in records:
            inviter = s.query(User).filter(User.id == r.inviter_id).first()
            new_user = s.query(User).filter(User.id == r.new_user_id).first()
            result.append({
                "id": r.id,
                "code": r.code,
                "reward_issued": r.reward_issued,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "inviter": {"id": inviter.id, "username": inviter.username} if inviter else None,
                "new_user": {"id": new_user.id, "username": new_user.username} if new_user else None
            })
        return result

@router.get("/api/admin/cleanup-expired")
async def cleanup_expired(request: Request):
    await require_admin(request)
    now = datetime.datetime.utcnow()
    deleted_count = 0
    with Session(engine) as s:
        expired_promos = s.query(PromoCode).filter(
            PromoCode.expires_at != None,
            PromoCode.expires_at < now
        ).all()
        deleted_count = len(expired_promos)
        for p in expired_promos:
            s.delete(p)
        s.commit()
    return {"message": f"已清理 {deleted_count} 个过期优惠码"}

# 优惠券规则相关API
@router.get("/api/admin/coupon-rules")
async def list_coupon_rules(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rules = s.query(CouponRule).order_by(CouponRule.created_at.desc()).all()
        result = []
        for r in rules:
            coupon = s.query(Coupon).filter(Coupon.id == r.coupon_id).first()
            result.append({
                "id": r.id,
                "name": r.name,
                "type": r.type,
                "coupon_id": r.coupon_id,
                "coupon_name": coupon.name if coupon else "",
                "give_count": r.give_count,
                "product_id": r.product_id,
                "category_id": r.category_id,
                "min_order_amount": r.min_order_amount,
                "enabled": r.enabled,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        return result

@router.post("/api/admin/coupon-rules")
async def create_coupon_rule(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rule = CouponRule(
            name=data["name"],
            type=data["type"],
            coupon_id=data["coupon_id"],
            give_count=data.get("give_count", 1),
            product_id=data.get("product_id"),
            category_id=data.get("category_id"),
            min_order_amount=data.get("min_order_amount", 0),
            enabled=data.get("enabled", True)
        )
        s.add(rule)
        s.commit()
        return {"message": "创建成功", "id": rule.id}

@router.put("/api/admin/coupon-rules/{rid}")
async def update_coupon_rule(rid: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rule = s.query(CouponRule).filter(CouponRule.id == rid).first()
        if not rule:
            raise HTTPException(404, "规则不存在")
        
        for key, value in data.items():
            setattr(rule, key, value)
        
        s.commit()
        return {"message": "更新成功"}

@router.delete("/api/admin/coupon-rules/{rid}")
async def delete_coupon_rule(rid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(CouponRule).filter(CouponRule.id == rid).delete()
        s.commit()
    return {"message": "已删除"}
