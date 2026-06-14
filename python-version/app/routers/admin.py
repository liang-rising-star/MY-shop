from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import engine
from app.models import User, AppSetting
from app.auth import require_admin

router = APIRouter()

# 公共API - 获取当前主题（无需登录）
@router.get("/api/site/theme")
async def get_site_theme():
    with Session(engine) as s:
        theme = s.query(AppSetting).filter(AppSetting.key == "site_theme").first()
        return {"theme": theme.value if theme else "cyberpunk"}

# 公共API - 获取完整网站设置（包含主题等）
@router.get("/api/site/settings")
async def get_site_settings():
    with Session(engine) as s:
        rows = s.query(AppSetting).all()
        settings = {}
        for r in rows:
            settings[r.key] = r.value
        return {"settings": settings}

@router.get("/api/admin/users")
async def list_users(request: Request, page: int = 1, page_size: int = 20, status: str = "", search: str = "", search_type: str = "username", sort: str = "created_at_desc"):
    await require_admin(request)
    with Session(engine) as s:
        q = s.query(User)
        if status:
            q = q.filter(User.status == status)
        if search:
            if search_type == "uuid":
                q = q.filter(User.uuid == search)
            else:
                q = q.filter(User.username.like(f"%{search}%"))
        sort_map = {
            "created_at_desc": User.created_at.desc(),
            "created_at_asc": User.created_at.asc(),
            "uuid_desc": User.uuid.desc(),
            "uuid_asc": User.uuid.asc(),
            "points_desc": User.points.desc(),
            "points_asc": User.points.asc(),
            "level_desc": User.level.desc(),
            "level_asc": User.level.asc(),
            "balance_desc": User.balance.desc(),
            "balance_asc": User.balance.asc(),
        }
        if sort == "role_desc":
            from sqlalchemy import case
            q = q.order_by(case((User.is_super_admin == True, 0), (User.is_admin == True, 1), else_=2).desc())
        elif sort == "role_asc":
            from sqlalchemy import case
            q = q.order_by(case((User.is_super_admin == True, 0), (User.is_admin == True, 1), else_=2).asc())
        elif sort in sort_map:
            q = q.order_by(sort_map[sort])
        else:
            q = q.order_by(User.id.desc())
        total = q.count()
        users = q.offset((page-1)*page_size).limit(page_size).all()
        return {
            "total": total, "page": page, "page_size": page_size,
            "users": [{c.name: getattr(u, c.name) for c in u.__table__.columns if c.name != "password"} for u in users]
        }

@router.put("/api/admin/users/{uid}/toggle-admin")
async def toggle_user_admin(uid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        user = s.query(User).filter(User.id == uid).first()
        if not user:
            raise HTTPException(404, "用户不存在")
        if user.is_super_admin:
            raise HTTPException(400, "超级管理员不能被取消管理员权限")
        user.is_admin = not user.is_admin
        s.commit()
        return {"message": "已更新", "is_admin": user.is_admin}

@router.put("/api/admin/users/{uid}/update")
async def update_user(uid: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        user = s.query(User).filter(User.id == uid).first()
        if not user:
            raise HTTPException(404, "用户不存在")
        admin_user = s.query(User).filter(User.id == request.state.user_id).first()
        admin_name = admin_user.username if admin_user else "unknown"
        changes = []
        if "username" in data and data["username"] != user.username:
            existing = s.query(User).filter(User.username == data["username"], User.id != uid).first()
            if existing:
                raise HTTPException(400, "用户名已存在")
            changes.append(f"用户名 {user.username}→{data['username']}")
            user.username = data["username"]
        if "uuid" in data and data["uuid"] != user.uuid:
            existing_uuid = s.query(User).filter(User.uuid == data["uuid"], User.id != uid).first()
            if existing_uuid:
                raise HTTPException(400, "UUID已存在")
            changes.append(f"UUID {user.uuid}→{data['uuid']}")
            user.uuid = data["uuid"]
        if "level" in data and data["level"] != user.level:
            changes.append(f"等级 {user.level}→{data['level']}")
            user.level = data["level"]
        if "points" in data and data["points"] != user.points:
            changes.append(f"积分 {user.points}→{data['points']}")
            user.points = data["points"]
        if "balance" in data and data["balance"] != user.balance:
            changes.append(f"余额 {user.balance}→{data['balance']}")
            user.balance = data["balance"]
        if "is_admin" in data:
            if not user.is_super_admin:
                old_admin = user.is_admin
                user.is_admin = data["is_admin"]
                if not data["is_admin"]:
                    user.admin_permissions = ""
                if old_admin != data["is_admin"]:
                    changes.append(f"管理员 {'是' if data['is_admin'] else '否'}")
        if "admin_permissions" in data and not user.is_super_admin:
            user.admin_permissions = data["admin_permissions"]
            changes.append("权限已更新")
        if "status" in data:
            old_status = user.status
            user.status = data["status"]
            if data["status"] == "banned" and not user.is_super_admin:
                user.is_admin = False
                user.admin_permissions = ""
            if old_status != data["status"]:
                changes.append(f"状态 {old_status}→{data['status']}")
        s.commit()
        if changes:
            from app import logger
            logger.log_admin_action(admin_name, admin_user.is_super_admin if admin_user else False, f"修改用户 {user.username}", detail="；".join(changes))
        return {"message": "已更新"}

@router.get("/api/admin/settings")
async def get_settings(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rows = s.query(AppSetting).all()
        return {r.key: r.value for r in rows}

@router.post("/api/admin/settings")
async def save_settings(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        for k, v in data.items():
            existing = s.query(AppSetting).filter(AppSetting.key == k).first()
            if existing: existing.value = str(v)
            else: s.add(AppSetting(key=k, value=str(v)))
        s.commit()
    return {"message": "设置已保存"}

@router.get("/api/admin/config")
async def get_config(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rows = s.query(AppSetting).filter(AppSetting.key.like("config_%")).all()
        config = {}
        for r in rows:
            key = r.key.replace("config_", "")
            try:
                if r.value == "True": config[key] = True
                elif r.value == "False": config[key] = False
                elif r.value.isdigit(): config[key] = int(r.value)
                else: config[key] = r.value
            except: config[key] = r.value
        return {"config": config}

@router.post("/api/admin/config")
async def save_config(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        for k, v in data.items():
            key = f"config_{k}"
            existing = s.query(AppSetting).filter(AppSetting.key == key).first()
            val = "True" if v is True else "False" if v is False else str(v)
            if existing: existing.value = val
            else: s.add(AppSetting(key=key, value=val))
        s.commit()
    return {"message": "设置已保存"}

@router.get("/api/admin/lottery")
async def get_lottery(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rows = s.query(AppSetting).filter(AppSetting.key.like("lottery_%")).all()
        settings = {}
        for r in rows:
            key = r.key.replace("lottery_", "")
            try:
                if r.value == "True": settings[key] = True
                elif r.value == "False": settings[key] = False
                elif r.value.isdigit(): settings[key] = int(r.value)
                elif r.value.startswith("["): 
                    import json
                    settings[key] = json.loads(r.value.replace("'", '"'))
                else: settings[key] = r.value
            except: settings[key] = r.value
        return {"settings": settings}

@router.post("/api/admin/lottery")
async def save_lottery(data: dict, request: Request):
    await require_admin(request)
    import json
    with Session(engine) as s:
        for k, v in data.items():
            key = f"lottery_{k}"
            if isinstance(v, (list, dict)):
                val = json.dumps(v)
            elif v is True: val = "True"
            elif v is False: val = "False"
            else: val = str(v)
            existing = s.query(AppSetting).filter(AppSetting.key == key).first()
            if existing: existing.value = val
            else: s.add(AppSetting(key=key, value=val))
        s.commit()
    return {"message": "抽奖设置已保存"}

@router.get("/api/admin/event")
async def get_event(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        rows = s.query(AppSetting).filter(AppSetting.key.like("event_%")).all()
        event = {}
        for r in rows:
            key = r.key.replace("event_", "")
            try:
                if r.value == "True": event[key] = True
                elif r.value == "False": event[key] = False
                elif r.value.isdigit(): event[key] = int(r.value)
                elif r.value.startswith("["):
                    import json
                    event[key] = json.loads(r.value.replace("'", '"'))
                else: event[key] = r.value
            except: event[key] = r.value
        return {"event": event}

@router.post("/api/admin/site/theme")
async def save_site_theme(data: dict, request: Request):
    await require_admin(request)
    theme = data.get("theme", "cyberpunk")
    with Session(engine) as s:
        existing = s.query(AppSetting).filter(AppSetting.key == "site_theme").first()
        if existing: existing.value = theme
        else: s.add(AppSetting(key="site_theme", value=theme))
        s.commit()
    return {"message": "主题已保存"}

@router.post("/api/admin/config/email/test")
async def test_email(data: dict, request: Request):
    await require_admin(request)
    email = data.get("email")
    if not email:
        return {"error": "请提供邮箱地址"}
    
    # 获取邮件配置
    with Session(engine) as s:
        def get_config(key, default=""):
            row = s.query(AppSetting).filter(AppSetting.key == f"config_{key}").first()
            return row.value if row else default
        
        smtp = get_config("email_smtp")
        port = get_config("email_port", "465")
        secure = get_config("email_secure", "ssl")
        username = get_config("email_username")
        password = get_config("email_password")
    
    if not smtp or not username or not password:
        return {"error": "请先配置邮件设置"}
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = email
        msg['Subject'] = 'MY-Shop 测试邮件'
        
        body = '''
        <html>
        <body>
            <h2>测试邮件发送成功！</h2>
            <p>这是一封来自 MY-Shop 后台管理系统的测试邮件。</p>
            <p>如果您收到这封邮件，说明邮件配置正确。</p>
            <p><small>发送时间: {}</small></p>
        </body>
        </html>
        '''.format(__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP_SSL(smtp, int(port)) if secure == 'ssl' else smtplib.SMTP(smtp, int(port))
        if secure == 'tls':
            server.starttls()
        server.login(username, password)
        server.sendmail(username, email, msg.as_string())
        server.quit()
        
        return {"message": f"测试邮件已发送到 {email}"}
    except Exception as e:
        return {"error": f"发送失败: {str(e)}"}

@router.post("/api/admin/config/sms/test")
async def test_sms(data: dict, request: Request):
    await require_admin(request)
    phone = data.get("phone")
    if not phone:
        return {"error": "请提供手机号"}
    
    # 获取短信配置
    with Session(engine) as s:
        def get_config(key, default=""):
            row = s.query(AppSetting).filter(AppSetting.key == f"config_{key}").first()
            return row.value if row else default
        
        platform = get_config("sms_platform", "aliyun")
    
    return {"message": f"短信测试功能需要配置 {platform} 短信服务，当前为模拟成功。请配置真实的短信服务商。"}

@router.post("/api/admin/event")
async def save_event(data: dict, request: Request):
    await require_admin(request)
    import json
    with Session(engine) as s:
        for k, v in data.items():
            key = f"event_{k}"
            if isinstance(v, (list, dict)):
                val = json.dumps(v)
            elif v is True: val = "True"
            elif v is False: val = "False"
            else: val = str(v)
            existing = s.query(AppSetting).filter(AppSetting.key == key).first()
            if existing: existing.value = val
            else: s.add(AppSetting(key=key, value=val))
        s.commit()
    return {"message": "活动设置已保存"}
