import uvicorn, os, shutil, mimetypes
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.database import init_db
from app.routers import setup, auth, products, categories, cardkeys, orders, coupons, admin, user_center, payment, levels, address, dashboard, lottery, events, bills, admin_logs

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/javascript', '.js')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@asynccontextmanager
async def lifespan(app: FastAPI):
    upload_dir = config.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    subdirs = [
        "temp", "images", "images/products", "images/logos", "images/others",
        "product_files", "zip_files", "software", "documents"
    ]
    
    for subdir in subdirs:
        full_path = os.path.join(upload_dir, subdir)
        os.makedirs(full_path, exist_ok=True)
    
    temp_dir = os.path.join(upload_dir, "temp")
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"清理temp文件夹时出错: {e}")
    
    init_db()
    from app import logger
    logger.log_server("info", "服务器启动成功", f"数据库初始化完成，监听端口 {config.PORT if hasattr(config, 'PORT') else 8080}")
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if hasattr(config, 'CORS_ORIGINS') else ["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "请求参数错误", "details": exc.errors()})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"Server Error: {exc}")
    traceback.print_exc()
    from app import logger
    logger.log_server("error", f"服务器错误: {str(exc)}", traceback.format_exc())
    if os.getenv("DEBUG", "false").lower() == "true":
        return JSONResponse(status_code=500, content={"error": "服务器内部错误", "details": str(exc)})
    return JSONResponse(status_code=500, content={"error": "服务器内部错误，请稍后重试"})

def forbidden_response():
    """返回403禁止访问页面"""
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
            <head><title>403 Forbidden</title></head>
            <body>
                <center><h1>403 Forbidden</h1></center>
                <hr><center>nginx</center>
            </body>
        </html>
        """,
        status_code=403
    )

def check_anti_crawler(request: Request, allow_empty_referer: bool = False):
    """检查爬虫和防盗链"""
    user_agent = request.headers.get("User-Agent") or request.headers.get("user-agent", "")
    if not user_agent or not user_agent.strip():
        raise HTTPException(status_code=403, detail="无效的请求")
    
    crawler_keywords = ['bot', 'crawler', 'spider', 'scrapy', 'curl', 'wget', 'python', 'go-http-client']
    user_agent_lower = user_agent.lower()
    for keyword in crawler_keywords:
        if keyword in user_agent_lower:
            raise HTTPException(status_code=403, detail="访问被拒绝")
    
    if not allow_empty_referer:
        referer = request.headers.get("Referer")
        host = request.headers.get("Host")
        
        if not referer:
            raise HTTPException(status_code=403, detail="不允许直接访问")
        
        from urllib.parse import urlparse
        try:
            referer_url = urlparse(referer)
            referer_host = referer_url.netloc
            if referer_host != host:
                raise HTTPException(status_code=403, detail="不允许盗链")
        except:
            raise HTTPException(status_code=403, detail="无效的请求")

# ========== 注册路由（先注册API路由）==========

for r in [setup, auth, products, categories, cardkeys, orders, coupons, admin, user_center, payment, levels, address, dashboard, lottery, events, bills, admin_logs]:
    app.include_router(r.router)

import json as _json

@app.get("/api/admin/logs")
async def get_admin_logs(request: Request, category: str = "all", page: int = 1, page_size: int = 50, level: str = "", sort: str = "time_desc"):
    from app.auth import require_admin
    await require_admin(request)
    log_dir = os.path.join(BASE_DIR, "logs")
    cats = ["server", "user_login", "admin_login", "user_action", "admin_action"] if category == "all" else [category]
    all_logs = []
    for cat in cats:
        f = os.path.join(log_dir, f"{cat}.json")
        if os.path.isfile(f):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    entries = _json.load(fh)
                if category == "all":
                    for entry in entries:
                        entry["category"] = cat
                        all_logs.append(entry)
                else:
                    all_logs.extend(entries)
            except:
                pass
    if level:
        all_logs = [l for l in all_logs if l.get("level") == level]
    all_logs.sort(key=lambda x: x.get("time", ""), reverse=(sort != "time_asc"))
    total = len(all_logs)
    items = all_logs[(page - 1) * page_size: page * page_size]
    return {"total": total, "page": page, "page_size": page_size, "logs": items}

@app.get("/api/admin/logs/retention")
async def get_log_retention(request: Request):
    from app.auth import require_admin
    await require_admin(request)
    from app.models import AppSetting
    from app.database import engine
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        row = s.query(AppSetting).filter(AppSetting.key == "log_retention_days").first()
        days = int(row.value) if row and row.value else 30
    return {"retention_days": days}

@app.post("/api/admin/logs/retention")
async def set_log_retention(data: dict, request: Request):
    from app.auth import require_admin
    await require_admin(request)
    from app.models import AppSetting
    from app.database import engine
    from sqlalchemy.orm import Session
    days = data.get("retention_days", 30)
    with Session(engine) as s:
        row = s.query(AppSetting).filter(AppSetting.key == "log_retention_days").first()
        if row:
            row.value = str(days)
        else:
            s.add(AppSetting(key="log_retention_days", value=str(days)))
        s.commit()
    import datetime as _dt
    cutoff = (_dt.datetime.now() - _dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    for cat in ["user_login", "admin_login", "user_action", "admin_action", "server"]:
        f = os.path.join(os.path.join(BASE_DIR, "logs"), f"{cat}.json")
        if not os.path.isfile(f):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                logs = _json.load(fh)
            filtered = [l for l in logs if l.get("time", "") >= cutoff]
            if len(filtered) != len(logs):
                with open(f, "w", encoding="utf-8") as fh:
                    _json.dump(filtered, fh, ensure_ascii=False)
        except:
            pass
    return {"message": "已保存"}

@app.post("/api/admin/logs/cleanup")
async def cleanup_logs(request: Request):
    from app.auth import require_admin
    await require_admin(request)
    from app.models import AppSetting
    from app.database import engine
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        row = s.query(AppSetting).filter(AppSetting.key == "log_retention_days").first()
        days = int(row.value) if row and row.value else 30
    import datetime as _dt
    cutoff = (_dt.datetime.now() - _dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    for cat in ["user_login", "admin_login", "user_action", "admin_action", "server"]:
        f = os.path.join(os.path.join(BASE_DIR, "logs"), f"{cat}.json")
        if not os.path.isfile(f):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                logs = _json.load(fh)
            filtered = [l for l in logs if l.get("time", "") >= cutoff]
            if len(filtered) != len(logs):
                with open(f, "w", encoding="utf-8") as fh:
                    _json.dump(filtered, fh, ensure_ascii=False)
        except:
            pass
    return {"message": "已清理过期日志"}

# ========== 静态文件服务（必须在路由之前挂载）==========

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")

# ========== 禁止访问的路径 ==========

@app.get("/uploads/{path:path}")
async def block_uploads(path: str = ""):
    return forbidden_response()

@app.get("/{filename}.py")
async def block_py_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.pyc")
async def block_pyc_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.db")
async def block_db_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.sqlite")
async def block_sqlite_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.env")
async def block_env_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.json")
async def block_json_files(filename: str = ""):
    if filename in ['i18n', 'locales', 'messages']:
        pass
    else:
        return forbidden_response()

@app.get("/{filename}.md")
async def block_md_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.txt")
async def block_txt_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.log")
async def block_log_files(filename: str = ""):
    return forbidden_response()

@app.get("/{filename}.gitignore")
async def block_gitignore(filename: str = ""):
    return forbidden_response()

@app.get("/.env")
async def block_dot_env():
    return forbidden_response()

@app.get("/.git")
async def block_git():
    return forbidden_response()

@app.get("/.DS_Store")
async def block_ds_store():
    return forbidden_response()

@app.get("/config.py")
async def block_config_py():
    return forbidden_response()

@app.get("/requirements.txt")
async def block_requirements_txt():
    return forbidden_response()

@app.get("/README.md")
async def block_readme():
    return forbidden_response()

@app.get("/LICENSE")
async def block_license():
    return forbidden_response()

# ========== Logo API（防盗链）==========

@app.get("/api/logo")
async def get_logo(request: Request):
    """获取网站Logo"""
    check_anti_crawler(request, allow_empty_referer=False)
    
    from app.database import engine
    from sqlalchemy.orm import Session
    from app.models import AppSetting
    
    with Session(engine) as s:
        logo_setting = s.query(AppSetting).filter(AppSetting.key == "logo").first()
        logo_path = logo_setting.value if logo_setting and logo_setting.value else ""
    
    if not logo_path:
        raise HTTPException(status_code=404, detail="Logo未设置")
    
    if logo_path.startswith('/uploads/'):
        relative_path = logo_path[9:]
        full_path = os.path.join(config.UPLOAD_DIR, relative_path)
    elif logo_path.startswith('/static/'):
        relative_path = logo_path[8:]
        full_path = os.path.join(BASE_DIR, "static", relative_path)
    else:
        full_path = os.path.join(config.UPLOAD_DIR, logo_path)
        if not os.path.exists(full_path):
            full_path = os.path.join(BASE_DIR, "static", logo_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Logo文件不存在")
    
    ext = os.path.splitext(full_path)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.ico': 'image/x-icon'
    }
    
    response = FileResponse(
        full_path,
        media_type=content_types.get(ext, 'application/octet-stream')
    )
    
    response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    
    return response

# ========== 背景图 API ==========

@app.get("/api/background")
async def get_background(request: Request, mobile: bool = False):
    """获取背景图"""
    check_anti_crawler(request, allow_empty_referer=False)
    
    from app.database import engine
    from sqlalchemy.orm import Session
    from app.models import AppSetting
    
    key = "background_mobile_url" if mobile else "background_url"
    
    with Session(engine) as s:
        bg_setting = s.query(AppSetting).filter(AppSetting.key == key).first()
        bg_path = bg_setting.value if bg_setting and bg_setting.value else ""
    
    if not bg_path:
        raise HTTPException(status_code=404, detail="背景图未设置")
    
    if bg_path.startswith('/uploads/'):
        relative_path = bg_path[9:]
        full_path = os.path.join(config.UPLOAD_DIR, relative_path)
    elif bg_path.startswith('/static/'):
        relative_path = bg_path[8:]
        full_path = os.path.join(BASE_DIR, "static", relative_path)
    else:
        full_path = os.path.join(config.UPLOAD_DIR, bg_path)
        if not os.path.exists(full_path):
            full_path = os.path.join(BASE_DIR, "static", bg_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="背景图不存在")
    
    ext = os.path.splitext(full_path)[1].lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    
    response = FileResponse(
        full_path,
        media_type=content_types.get(ext, 'application/octet-stream')
    )
    
    response.headers["Cache-Control"] = "public, max-age=86400"
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    return response

# ========== 图片访问 API ==========

@app.get("/api/image/{file_path:path}")
async def get_image_via_api(file_path: str, request: Request):
    """通过API访问图片"""
    check_anti_crawler(request, allow_empty_referer=False)
    
    full_path = os.path.join(config.UPLOAD_DIR, file_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.realpath(full_path).startswith(os.path.realpath(config.UPLOAD_DIR)):
        raise HTTPException(status_code=403, detail="访问被拒绝")
    
    ext = os.path.splitext(full_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', '.ico'}
    if ext not in image_exts:
        raise HTTPException(status_code=403, detail="仅允许访问图片文件")
    
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
        '.ico': 'image/x-icon'
    }
    
    response = FileResponse(
        full_path,
        media_type=content_types.get(ext, 'application/octet-stream')
    )
    
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "same-origin"
    
    return response

# ========== 文件下载 API ==========

@app.get("/api/download/{file_path:path}")
async def download_file_via_api(file_path: str, request: Request):
    """通过API下载文件"""
    from app.auth import get_current_user
    user = await get_current_user(request)
    
    full_path = os.path.join(config.UPLOAD_DIR, file_path)
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.realpath(full_path).startswith(os.path.realpath(config.UPLOAD_DIR)):
        raise HTTPException(status_code=403, detail="访问被拒绝")
    
    filename = os.path.basename(full_path)
    
    return FileResponse(
        full_path,
        filename=filename,
        media_type='application/octet-stream'
    )

# ========== 前端页面路由（必须在最后）==========

@app.get("/")
def home():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/admin-login")
async def admin_login_page():
    return FileResponse(os.path.join(BASE_DIR, "static", "admin-login.html"))

@app.get("/admin")
@app.get("/admin/{path:path}")
async def admin_page(path: str = ""):
    return FileResponse(os.path.join(BASE_DIR, "static", "admin.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/{path:path}")
def serve_frontend(path: str = ""):
    """通用的前端路由"""
    if path.startswith("api/"):
        return forbidden_response()
    # 尝试作为静态文件返回
    file_path = os.path.join(BASE_DIR, "static", path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    # 否则返回index.html（SPA模式）
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
