import datetime, random, string
import io, base64
import uuid as uuid_lib
from PIL import Image, ImageDraw, ImageFont
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import engine
from app.models import User, AppSetting
from app.auth import hash_password, verify_password, create_token, get_current_user

def gen_invite():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

router = APIRouter()

CAPTCHA_CACHE = {}

def generate_captcha_image(code: str) -> str:
    width, height = 120, 40
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    for i, char in enumerate(code):
        x = 10 + i * 25 + random.randint(-3, 3)
        y = random.randint(5, 10)
        draw.text((x, y), char, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)), font=font)
    for _ in range(30):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), width=1)
    buf = io.BytesIO()
    image.save(buf, 'PNG')
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

@router.get("/api/captcha")
def get_captcha():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    CAPTCHA_CACHE[key] = {"code": code, "expire": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)}
    image = generate_captcha_image(code)
    return {"key": key, "image": image}

def verify_captcha(key: str, code: str) -> bool:
    if key not in CAPTCHA_CACHE:
        return False
    captcha = CAPTCHA_CACHE[key]
    if datetime.datetime.utcnow() > captcha["expire"]:
        del CAPTCHA_CACHE[key]
        return False
    if captcha["code"].upper() == code.upper():
        del CAPTCHA_CACHE[key]
        return True
    return False

@router.post("/api/register")
def register(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "")
    captcha_key = data.get("captcha_key", "")
    captcha_code = data.get("captcha_code", "")
    
    if not username or len(username) < 3:
        raise HTTPException(400, "用户名至少需要3个字符")
    if len(username) > 50:
        raise HTTPException(400, "用户名最多50个字符")
    if not password or len(password) < 6:
        raise HTTPException(400, "密码至少需要6个字符")
    if not verify_captcha(captcha_key, captcha_code):
        raise HTTPException(400, "验证码错误")
    
    invite_code = data.get("invite_code", "")
    invite_uid = None
    inviter = None
    with Session(engine) as s:
        if s.query(User).filter(User.username == username).first():
            raise HTTPException(409, "用户名已存在")
        if invite_code:
            inviter = s.query(User).filter(User.invite_code == invite_code).first()
            if inviter:
                invite_uid = inviter.id
                inviter.team_count = (inviter.team_count or 0) + 1
        # 生成递增UUID
        max_uuid_user = s.query(User.uuid).filter(User.uuid != None, User.uuid != "0").order_by(User.id.desc()).first()
        try:
            next_uuid = int(max_uuid_user[0]) + 1 if max_uuid_user and max_uuid_user[0] and max_uuid_user[0].isdigit() else 1
        except:
            next_uuid = 1
        u = User(username=username, password=hash_password(password), email=data.get("email",""), invite_code=gen_invite(), invite_uid=invite_uid, uuid=str(next_uuid))
        s.add(u)
        s.flush()
        
        # 第一个注册的用户自动成为超级管理员
        user_count = s.query(User).count()
        if user_count == 1:
            u.is_admin = True
            u.is_super_admin = True
            u.uuid = "0"
        
        # 处理邀请奖励
        if inviter:
            from app.models import AppSetting, Coupon, UserCoupon, InviteRecord
            # 保存邀请记录
            record = InviteRecord(
                inviter_id=inviter.id,
                new_user_id=u.id,
                code=invite_code
            )
            s.add(record)
            
            # 获取邀请设置
            reward_new_user = 0
            reward_inviter = 0
            reward_coupon_id = None
            reward_coupon_count = 1
            for key in ["reward_new_user", "reward_inviter", "reward_coupon", "reward_coupon_count"]:
                row = s.query(AppSetting).filter(AppSetting.key == f"invite_{key}").first()
                if row:
                    if key == "reward_coupon":
                        reward_coupon_id = int(row.value) if row.value else None
                    elif key == "reward_coupon_count":
                        reward_coupon_count = int(row.value) if row.value else 1
                    else:
                        try:
                            val = int(row.value)
                            if key == "reward_new_user":
                                reward_new_user = val
                            elif key == "reward_inviter":
                                reward_inviter = val
                        except:
                            pass
            
            # 发放新用户奖励
            if reward_new_user > 0:
                u.points = (u.points or 0) + reward_new_user
            
            # 发放邀请人奖励
            if reward_inviter > 0 and inviter:
                inviter.points = (inviter.points or 0) + reward_inviter
            
            # 发放优惠券
            if reward_coupon_id:
                coupon = s.query(Coupon).filter(Coupon.id == reward_coupon_id).first()
                if coupon:
                    # 给新用户发优惠券
                    for _ in range(reward_coupon_count):
                        uc = UserCoupon(user_id=u.id, coupon_id=coupon.id)
                        s.add(uc)
                    record.reward_issued = True
        
        s.commit()
        return {"message": "注册成功", "user_id": u.id}

@router.post("/api/login")
def login(data: dict, request: Request):
    username = data.get("username", "").strip()
    password = data.get("password", "")
    captcha_key = data.get("captcha_key", "")
    captcha_code = data.get("captcha_code", "")
    is_admin_login = data.get("is_admin", False)
    ip = request.client.host if request.client else "unknown"
    
    if not username or not password:
        raise HTTPException(400, "用户名和密码不能为空")
    
    if captcha_key and captcha_code:
        if not verify_captcha(captcha_key, captcha_code):
            raise HTTPException(400, "验证码错误")
    
    with Session(engine) as s:
        u = s.query(User).filter(User.username == username).first()
        if not u or not verify_password(password, u.password):
            from app import logger
            if is_admin_login:
                logger.log_admin_login(username, ip, False, reason="用户名或密码错误")
            else:
                logger.log_user_login(username, ip, False, reason="用户名或密码错误")
            raise HTTPException(401, "用户名或密码错误")
        if u.status != "normal":
            from app import logger
            if u.is_admin:
                logger.log_admin_login(username, ip, False, is_super=u.is_super_admin, reason="账户已被禁用")
            else:
                logger.log_user_login(username, ip, False, reason="账户已被禁用")
            raise HTTPException(403, "账户已被禁用")
        
        from app import logger
        if u.is_admin:
            logger.log_admin_login(username, ip, True, is_super=u.is_super_admin)
        else:
            logger.log_user_login(username, ip, True)
        
        admin_expire = None
        if u.is_admin:
            row = s.query(AppSetting).filter(AppSetting.key == "config_admin_session_expire").first()
            if row and row.value:
                try: admin_expire = int(row.value)
                except: pass
        token = create_token(u.id, u.is_admin, admin_expire)
        resp_data = {"token": token, "user_id": u.id, "level": u.level, "is_admin": u.is_admin}
        if u.is_admin:
            response = JSONResponse(content=resp_data)
            response.set_cookie(key="admin_token", value=token, max_age=86400, httponly=True, samesite="lax", path="/")
            return response
        return resp_data

@router.get("/api/profile")
async def profile(request: Request):
    await get_current_user(request)
    with Session(engine) as s:
        u = s.query(User).filter(User.id == request.state.user_id).first()
        if not u:
            raise HTTPException(401, "用户不存在")
        return {c.name: getattr(u, c.name) for c in u.__table__.columns if c.name != "password"}
