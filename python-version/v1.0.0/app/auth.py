import datetime, jwt, bcrypt
from fastapi import Request, HTTPException
from app.config import config
import logging

logger = logging.getLogger(__name__)

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS)).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def create_token(user_id: int, is_admin: bool = False, exp_minutes: int = None) -> str:
    if is_admin and exp_minutes:
        exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=exp_minutes)
    elif is_admin:
        exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    else:
        exp = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    return jwt.encode({
        "user_id": user_id, "is_admin": is_admin,
        "exp": exp,
    }, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])

async def get_current_user(request: Request, require_admin: bool = False):
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get("admin_token")
    if not token:
        logger.warning(f"No auth token from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(401, "需要登录")
    try:
        data = decode_token(token)
        request.state.user_id = data["user_id"]
        request.state.is_admin = data.get("is_admin", False)
        logger.info(f"User {request.state.user_id} authenticated, is_admin={request.state.is_admin}")
        if require_admin and not request.state.is_admin:
            raise HTTPException(403, "需要管理员权限")
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(401, "登录已过期")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(401, "登录已过期")
    except Exception as e:
        logger.warning(f"Auth error: {e}")
        raise HTTPException(401, "登录已过期")

async def require_admin(request: Request):
    await get_current_user(request, require_admin=True)
