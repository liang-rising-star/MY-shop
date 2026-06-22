from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.database import engine
from app.models import User
from app.auth import hash_password

router = APIRouter()

@router.get("/api/setup/status")
def setup_status():
    with Session(engine) as s:
        exists = s.query(User).filter(User.is_admin == True).first()
        return {"setup_required": exists is None}

@router.post("/api/setup/init")
def setup_init(data: dict):
    with Session(engine) as s:
        if s.query(User).filter(User.is_admin == True).first():
            raise HTTPException(400, "管理员已存在")
        u = User(username=data["username"], password=hash_password(data["password"]),
                 email=data.get("email", ""), is_admin=True, level=3)
        s.add(u); s.commit()
        return {"message": "管理员创建成功", "user_id": u.id}
