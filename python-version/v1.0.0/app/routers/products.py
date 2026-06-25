from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from app.database import engine
from app.models import Product, ProductCategory, CardKey, BlindBoxPool, ProductSku, RecommendProduct, ProductFile, AppSetting
from app.auth import require_admin
from app.config import config
from app.data_integrity import record_missing_file, get_open_issues, resolve_issue, get_open_count
import os, uuid, shutil, datetime, json, zipfile

router = APIRouter()

def get_product_dir(pid):
    """获取商品数据目录"""
    d = os.path.join(config.SHOP_DATA_DIR, str(pid))
    for sub in ["media/video/vedio", "media/video/show_frame", "media/image", "bakup"]:
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    return d

def ensure_product_file_dir(pid):
    """有需要时创建 file 目录"""
    d = os.path.join(config.SHOP_DATA_DIR, str(pid), "file")
    os.makedirs(d, exist_ok=True)
    return d

def _migrate_product_files(pid, data):
    """将临时目录的文件迁移到 shop/<pid>/media/ 下，并清理临时目录"""
    get_product_dir(pid)
    updates = {}
    temp_dirs_to_clean = set()
    task_id = data.get("task_id", "")

    for field, is_video, sub_dir in [
        ("images", False, "image"),
        ("video_url", True, "video/vedio"),
        ("video_thumbnails", True, "video/show_frame"),
    ]:
        urls = data.get(field, "")
        if not urls:
            continue
        parts = [u.strip() for u in urls.split(",") if u.strip()]
        new_parts = []
        for url in parts:
            if not url.startswith("/api/resource/uploads_temp/"):
                new_parts.append(url)
                continue
            basename = os.path.basename(url)
            parts_from_url = url.replace("/api/resource/uploads_temp/", "").split("/")
            if len(parts_from_url) < 2:
                new_parts.append(url)
                continue
            task_id = parts_from_url[0]
            temp_dirs_to_clean.add(task_id)

            dest_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", sub_dir)
            os.makedirs(dest_dir, exist_ok=True)
            if sub_dir == "video/vedio":
                prefix = f"VID_{pid}_"
            elif sub_dir == "video/show_frame":
                prefix = f"SF_{pid}_"
            else:
                prefix = f"IMG_{pid}_"
            existing = [f for f in os.listdir(dest_dir) if f.startswith(prefix)]
            next_id = max([int(f.split("_")[-1].split(".")[0]) for f in existing if f.split("_")[-1].split(".")[0].isdigit()] or [0]) + 1
            ext = os.path.splitext(basename)[1]
            new_name = f"{prefix}{next_id}{ext}"
            src = os.path.join(config.TEMP_DIR, task_id, basename)
            dst = os.path.join(dest_dir, new_name)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                try: os.remove(src)
                except OSError: pass
            new_url = f"/api/resource/shop/{pid}/media/{sub_dir}/{new_name}"
            new_parts.append(new_url)
            if field == "images" and not updates.get("image_url"):
                updates["image_url"] = new_url

        if new_parts != parts:
            updates[field] = ",".join(new_parts)

    if updates:
        with Session(engine) as s:
            p = s.query(Product).filter(Product.id == pid).first()
            if p:
                for k, v in updates.items():
                    setattr(p, k, v)
                s.commit()

    for task_id in temp_dirs_to_clean:
        task_dir = os.path.join(config.TEMP_DIR, task_id)
        if os.path.isdir(task_dir):
            shutil.rmtree(task_dir, ignore_errors=True)
    if task_id and task_id not in temp_dirs_to_clean:
        task_dir = os.path.join(config.TEMP_DIR, task_id)
        if os.path.isdir(task_dir):
            shutil.rmtree(task_dir, ignore_errors=True)

def save_product_backup(pid, product_data):
    """保存商品备份到 bakup.json"""
    try:
        d = get_product_dir(pid)
        bakup_path = os.path.join(d, "bakup", "bakup.json")
        with open(bakup_path, "w", encoding="utf-8") as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[Backup Error] product {pid}: {e}")

def is_discount_active(product):
    """检查折扣是否有效"""
    mode = getattr(product, 'discount_mode', 'none') or 'none'
    if mode == 'percent':
        pct = getattr(product, 'discount_percent', 0) or 0
        return pct > 0 and pct < 100
    if mode == 'fixed':
        dp = product.discount_price
        if not dp or dp <= 0:
            return False
        return dp < product.price
    return False

def get_display_price(product):
    """获取显示价格（考虑折扣）"""
    mode = getattr(product, 'discount_mode', 'none') or 'none'
    if mode == 'percent':
        pct = getattr(product, 'discount_percent', 0) or 0
        if pct > 0 and pct < 100:
            return round(product.price * pct / 100, 2)
    if mode == 'fixed':
        dp = product.discount_price
        if dp and dp > 0 and dp < product.price:
            return dp
    return product.price

def get_original_display_price(product):
    """获取原价显示（有折扣时显示原价）"""
    if is_discount_active(product):
        return product.price
    return None

def get_discount_badge(product):
    """获取折扣标签"""
    mode = getattr(product, 'discount_mode', 'none') or 'none'
    if mode == 'percent':
        pct = getattr(product, 'discount_percent', 0) or 0
        if pct > 0 and pct < 100:
            return {"type": "discount", "text": "限时折扣", "color": "danger"}
    if mode == 'fixed':
        dp = product.discount_price
        if dp and dp > 0 and dp < product.price:
            return {"type": "discount", "text": "降价", "color": "danger"}
    if product.is_seckill:
        return {"type": "seckill", "text": "秒杀", "color": "danger"}
    if product.is_hot:
        return {"type": "hot", "text": "热卖", "color": "warning"}
    if product.is_new:
        return {"type": "new", "text": "新品", "color": "primary"}
    if product.is_recommend:
        return {"type": "recommend", "text": "推荐", "color": "success"}
    return None

@router.get("/api/products")
def list_products(category_id: int = 0, type: str = "", featured: int = 0, search: str = "", page: int = 1, page_size: int = 20):
    with Session(engine) as s:
        q = s.query(Product).filter(Product.is_active == True)
        if category_id: q = q.filter(Product.category_id == category_id)
        if type: q = q.filter(Product.type == type)
        if featured: q = q.filter(Product.featured == True)
        if search: q = q.filter(Product.name.contains(search))
        total = q.count()
        products = q.options(joinedload(Product.category)).order_by(Product.sort_order.desc(), Product.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        result = []
        for p in products:
            available_count = s.query(CardKey).filter(CardKey.product_id == p.id, CardKey.status == "available").count()
            total_count = s.query(CardKey).filter(CardKey.product_id == p.id).count()
            d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
            d["category"] = {"id": p.category.id, "name": p.category.name} if p.category else None
            d["available_stock"] = available_count
            d["card_key_count"] = available_count
            d["display_price"] = get_display_price(p)
            d["original_display_price"] = get_original_display_price(p)
            d["badge"] = get_discount_badge(p)
            d["is_discount_active"] = is_discount_active(p)
            result.append(d)
        return {"products": result, "total": total, "page": page, "page_size": page_size}

@router.get("/api/products/{pid}")
def get_product(pid: int):
    with Session(engine) as s:
        p = s.query(Product).options(joinedload(Product.category)).filter(Product.id == pid).first()
        if not p: raise HTTPException(404, "商品不存在")
        p.view_count += 1
        s.commit()
        cnt = s.query(CardKey).filter(CardKey.product_id == pid, CardKey.status == "available").count()
        pool = s.query(BlindBoxPool).options(joinedload(BlindBoxPool.prize)).filter(BlindBoxPool.product_id == pid).all()
        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        d["category"] = {"id": p.category.id, "name": p.category.name} if p.category else None
        d["available_stock"] = cnt
        d["card_key_count"] = cnt
        d["display_price"] = get_display_price(p)
        d["original_display_price"] = get_original_display_price(p)
        d["badge"] = get_discount_badge(p)
        d["is_discount_active"] = is_discount_active(p)
        d["pool"] = [{"id": e.id, "prize": {c.name: getattr(e.prize, c.name) for c in e.prize.__table__.columns} if e.prize else None, "probability": e.probability} for e in pool]
        return {"product": d, "card_key_count": cnt, "available": True, "pool": d["pool"]}

@router.post("/api/admin/products")
async def create_product(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        def parse_dt(v):
            if not v or v == '':
                return None
            return v
        p = Product(
            name=data["name"], 
            short_description=data.get("short_description",""),
            description=data.get("description",""),
            content=data.get("content",""),
            price=data["price"],
            original_price=data.get("original_price"),
            cost_price=data.get("cost_price"),
            discount=data.get("discount",0),
            discount_mode=data.get("discount_mode","none"),
            discount_percent=data.get("discount_percent",0),
            discount_price=data.get("discount_price"),
            discount_start=parse_dt(data.get("discount_start")),
            discount_end=parse_dt(data.get("discount_end")),
            category_id=data.get("category_id",0), 
            image_url=data.get("image_url",""),
            images=data.get("images",""),
            video_url=data.get("video_url",""),
            featured=data.get("featured",False),
            is_hot=data.get("is_hot",False),
            is_new=data.get("is_new",False),
            is_recommend=data.get("is_recommend",False),
            is_seckill=data.get("is_seckill",False),
            type=data.get("type","normal"),
            stock=data.get("stock",-1),
            stock_warning=data.get("stock_warning",10),
            max_buy_limit=data.get("max_buy_limit",0),
            per_user_limit=data.get("per_user_limit",0),
            delivery_type=data.get("delivery_type","card_key"),
            file_path=data.get("file_path",""),
            file_name=data.get("file_name",""),
            file_size=data.get("file_size",""),
            auto_delivery_content=data.get("auto_delivery_content",""),
            is_active=data.get("is_active",True),
            sort_order=data.get("sort_order",0),
            seo_title=data.get("seo_title",""),
            seo_keywords=data.get("seo_keywords",""),
            seo_description=data.get("seo_description",""),
            tags=data.get("tags",""),
            buy_notice=data.get("buy_notice",""),
            after_sale_notice=data.get("after_sale_notice",""),
            start_at=parse_dt(data.get("start_at")),
            end_at=parse_dt(data.get("end_at"))
        )
        s.add(p); s.commit()
        save_product_backup(p.id, {c.name: getattr(p, c.name) for c in p.__table__.columns})
        _migrate_product_files(p.id, data)
        return {c.name: getattr(p, c.name) for c in p.__table__.columns}

@router.put("/api/admin/products/{pid}")
async def update_product(pid: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        p = s.query(Product).filter(Product.id == pid).first()
        if not p: raise HTTPException(404)
        dt_fields = {'discount_start','discount_end','start_at','end_at'}
        for k, v in data.items():
            if hasattr(p, k):
                if k in dt_fields and (not v or v == ''):
                    v = None
                setattr(p, k, v)
        p.updated_at = datetime.datetime.utcnow()
        s.commit()
        save_product_backup(pid, {c.name: getattr(p, c.name) for c in p.__table__.columns})
        return {c.name: getattr(p, c.name) for c in p.__table__.columns}

@router.delete("/api/admin/products/{pid}")
async def delete_product(pid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        # 获取商品信息用于删除文件
        product = s.query(Product).filter(Product.id == pid).first()
        if product:
            # 删除图片/视频文件
            import glob as globmod
            if product.images:
                for img in product.images.split(","):
                    img = img.strip()
                    if img and img.startswith("/api/resource/"):
                        rel = img.replace("/api/resource/", "")
                        for base in [config.UPLOAD_DIR, config.SHOP_DATA_DIR, config.DATA_DIR]:
                            fp = os.path.join(base, rel)
                            if os.path.exists(fp):
                                try: os.remove(fp)
                                except: pass
                                break
            if product.video_url and product.video_url.startswith("/api/resource/"):
                rel = product.video_url.replace("/api/resource/", "")
                for base in [config.UPLOAD_DIR, config.SHOP_DATA_DIR, config.DATA_DIR]:
                    fp = os.path.join(base, rel)
                    if os.path.exists(fp):
                        try: os.remove(fp)
                        except: pass
                        break
            # 删除商品文件
            files = s.query(ProductFile).filter(ProductFile.product_id == pid).all()
            for f in files:
                if f.file_path and os.path.exists(f.file_path):
                    try: os.remove(f.file_path)
                    except: pass
        s.query(CardKey).filter(CardKey.product_id == pid, CardKey.status == "available").delete()
        s.query(BlindBoxPool).filter(BlindBoxPool.product_id == pid).delete()
        s.query(ProductFile).filter(ProductFile.product_id == pid).delete()
        s.query(Product).filter(Product.id == pid).delete()
        s.commit()
        product_dir = os.path.join(config.SHOP_DATA_DIR, str(pid))
        if os.path.exists(product_dir):
            try: shutil.rmtree(product_dir)
            except: pass
    return {"message": "已删除"}

@router.delete("/api/admin/products/{pid}/delete-file")
async def delete_product_file_by_url(pid: int, data: dict, request: Request):
    await require_admin(request)
    file_url = data.get("file", "")
    if file_url and file_url.startswith("/api/resource/"):
        rel = file_url.replace("/api/resource/", "")
        for base in [config.UPLOAD_DIR, config.SHOP_DATA_DIR, config.DATA_DIR]:
            fp = os.path.join(base, rel)
            if os.path.exists(fp):
                try: os.remove(fp)
                except: pass
                break
    return {"message": "已删除"}

@router.put("/api/admin/products/{pid}/blindbox")
async def update_pool(pid: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(BlindBoxPool).filter(BlindBoxPool.product_id == pid).delete()
        for e in data["entries"]:
            s.add(BlindBoxPool(product_id=pid, prize_id=e["prize_id"], probability=e["probability"]))
        p = s.query(Product).filter(Product.id == pid).first()
        if p:
            s.commit()
            save_product_backup(pid, {c.name: getattr(p, c.name) for c in p.__table__.columns})
        else:
            s.commit()
    return {"message": "奖池已更新"}

@router.post("/api/admin/upload")
async def upload_file(request: Request, file: UploadFile = File(...), file_type: str = Form(default="image"), product_id: int = Form(default=0), task_id: str = Form(default="")):
    await require_admin(request)
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', '.ico', '.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'}
    
    with Session(engine) as s:
        setting = s.query(AppSetting).filter(AppSetting.key == "config_upload_max_size").first()
        max_file_size = (int(setting.value) if setting else 1024) * 1024 * 1024
    
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(400, f"不支持的文件类型: {ext}")
    
    content = await file.read()
    if len(content) > max_file_size:
        raise HTTPException(400, f"文件大小超过限制")
    
    is_video = ext in ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp')
    
    if product_id > 0:
        pid = product_id
        if file_type == "logo":
            target_dir = os.path.join(config.UPLOAD_DIR, "images", "logos")
            name = f"{uuid.uuid4().hex}{ext}"
        else:
            if is_video:
                target_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", "video", "vedio")
                prefix = f"VID_{pid}_"
            else:
                target_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", "image")
                prefix = f"IMG_{pid}_"
            os.makedirs(target_dir, exist_ok=True)
            existing = [f for f in os.listdir(target_dir) if f.startswith(prefix)]
            next_id = max([int(f.split("_")[-1].split(".")[0]) for f in existing if f.split("_")[-1].split(".")[0].isdigit()] or [0]) + 1
            name = f"{prefix}{next_id}{ext}"
    elif task_id:
        target_dir = os.path.join(config.TEMP_DIR, task_id)
        os.makedirs(target_dir, exist_ok=True)
        name = f"{uuid.uuid4().hex}{ext}"
    else:
        if file_type == "logo":
            target_dir = os.path.join(config.UPLOAD_DIR, "images", "logos")
        else:
            target_dir = os.path.join(config.UPLOAD_DIR, "images", "others")
        os.makedirs(target_dir, exist_ok=True)
        name = f"{uuid.uuid4().hex}{ext}"
    
    path = os.path.join(target_dir, name)
    with open(path, "wb") as f:
        f.write(content)
    
    if product_id > 0:
        if is_video:
            rel_path = f"shop/{pid}/media/video/vedio/{name}"
        else:
            rel_path = f"shop/{pid}/media/image/{name}"
    elif task_id:
        rel_path = f"uploads_temp/{task_id}/{name}"
    else:
        rel_path = os.path.relpath(path, config.UPLOAD_DIR).replace("\\", "/").replace("\\", "/")
    
    thumb_url = ""
    if is_video:
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ret, frame = cap.read()
                if ret:
                    h, w = frame.shape[:2]
                    if max(h, w) > 200:
                        scale = 200 / max(h, w)
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                    if product_id > 0:
                        thumb_dir = os.path.join(config.SHOP_DATA_DIR, str(product_id), "media", "video", "show_frame")
                        os.makedirs(thumb_dir, exist_ok=True)
                        existing_sf = [f for f in os.listdir(thumb_dir) if f.startswith(f"SF_{product_id}_")]
                        next_sf_id = max([int(f.split("_")[-1].split(".")[0]) for f in existing_sf if f.split("_")[-1].split(".")[0].isdigit()] or [0]) + 1
                        thumb_name = f"SF_{product_id}_{next_sf_id}.jpg"
                    else:
                        thumb_dir = os.path.join(config.UPLOAD_DIR, "images", "others")
                        os.makedirs(thumb_dir, exist_ok=True)
                        thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_name)
                    cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    cap.release()
                    if product_id > 0:
                        thumb_url = f"/api/resource/shop/{product_id}/media/video/show_frame/{thumb_name}"
                    else:
                        thumb_rel = os.path.relpath(thumb_path, config.UPLOAD_DIR).replace("\\", "/")
                        thumb_url = f"/api/resource/{thumb_rel}"
                cap.release()
        except Exception as e:
            print(f"[Thumbnail Error] {e}")
    
    return {
        "url": f"/api/resource/{rel_path}",
        "path": path,
        "relative_path": rel_path,
        "thumbnail": thumb_url
    }

@router.post("/api/admin/upload/cleanup")
async def cleanup_temp_files(request: Request, data: dict):
    await require_admin(request)
    task_id = data.get("task_id", "")
    if task_id:
        task_dir = os.path.join(config.TEMP_DIR, task_id)
        if os.path.isdir(task_dir):
            shutil.rmtree(task_dir, ignore_errors=True)
    return {"message": "已清理"}

@router.get("/api/admin/products/{pid}/thumbnail")
async def generate_video_thumbnail(pid: int, request: Request, video_url: str = ""):
    """为视频生成缩略图（支持前台访问）"""
    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid).first()
        if not product:
            raise HTTPException(404, "商品不存在")
        if not video_url:
            full_url = product.video_url or ""
            if not full_url:
                raise HTTPException(400, "该商品没有视频")
            video_url = full_url.split(",")[0].strip()
        
        video_path = ""
        basename = os.path.basename(video_url) if video_url else ""
        
        vedio_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", "video", "vedio")
        if os.path.isdir(vedio_dir) and basename:
            for f in os.listdir(vedio_dir):
                if f == basename:
                    video_path = os.path.join(vedio_dir, f)
                    break
        
        if not video_path and video_url.startswith("/api/resource/"):
            rel = video_url.replace("/api/resource/", "")
            candidate = os.path.join(config.UPLOAD_DIR, rel)
            if os.path.isfile(candidate):
                video_path = candidate
        
        if not video_path:
            raise HTTPException(404, "视频文件不存在")
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ret, frame = cap.read()
                if ret:
                    h, w = frame.shape[:2]
                    if max(h, w) > 200:
                        scale = 200 / max(h, w)
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                    thumb_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", "video", "show_frame")
                    os.makedirs(thumb_dir, exist_ok=True)
                    thumb_name = f"SF_{pid}_{uuid.uuid4().hex}.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_name)
                    cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    cap.release()
                    return {"thumbnail": f"/api/resource/shop/{pid}/media/video/show_frame/{thumb_name}"}
                cap.release()
            raise HTTPException(500, "无法读取视频帧")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"生成缩略图失败: {str(e)}")

@router.get("/api/admin/products/{pid}/thumbnails")
async def batch_video_thumbnails(pid: int, request: Request, video_urls: str = ""):
    """批量获取视频缩略图"""
    if not video_urls:
        raise HTTPException(400, "缺少 video_urls 参数")
    urls = [u.strip() for u in video_urls.split(",") if u.strip()]
    result = {}
    for url in urls:
        video_path = ""
        basename = os.path.basename(url)
        for base in [config.UPLOAD_DIR, config.SHOP_DATA_DIR, config.DATA_DIR]:
            candidate = os.path.join(base, url.replace("/api/resource/", ""))
            if os.path.isfile(candidate):
                video_path = candidate
                break
        if not video_path and basename:
            vedio_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", "video", "vedio")
            if os.path.isdir(vedio_dir):
                for f in os.listdir(vedio_dir):
                    if f == basename:
                        video_path = os.path.join(vedio_dir, f)
                        break
        if not video_path:
            continue
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ret, frame = cap.read()
                if ret:
                    thumb_dir = os.path.join(config.SHOP_DATA_DIR, str(pid), "media", "video", "show_frame")
                    os.makedirs(thumb_dir, exist_ok=True)
                    thumb_name = f"SF_{pid}_{uuid.uuid4().hex}.jpg"
                    thumb_path = os.path.join(thumb_dir, thumb_name)
                    h, w = frame.shape[:2]
                    if max(h, w) > 200:
                        scale = 200 / max(h, w)
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                    cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    cap.release()
                    result[url] = f"/api/resource/shop/{pid}/media/video/show_frame/{thumb_name}"
                    continue
                cap.release()
        except Exception:
            pass
    return {"thumbnails": result}

# 批量上传商品文件（先存到temp）
@router.post("/api/admin/products/{pid}/upload-files")
async def upload_multiple_files(pid: int, request: Request, files: list[UploadFile] = File(...)):
    await require_admin(request)
    
    # 确保temp目录存在
    temp_dir = config.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)
    
    uploaded_files = []
    
    for file in files:
        content = await file.read()
        ext = os.path.splitext(file.filename)[1].lower()
        name = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(temp_dir, name)
        
        with open(path, "wb") as f:
            f.write(content)
        
        uploaded_files.append({
            "original_name": file.filename,
            "temp_name": name,
            "temp_path": path,
            "size": len(content)
        })
    
    return {"uploaded_files": uploaded_files}

# 清空temp文件夹
@router.post("/api/admin/clear-temp")
async def clear_temp_folder(request: Request):
    await require_admin(request)
    
    temp_dir = config.TEMP_DIR
    cleared_count = 0
    
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    cleared_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"删除文件时出错: {e}")
    
    return {"cleared": cleared_count}

@router.get("/api/products/{pid}/skus")
def list_skus(pid: int):
    with Session(engine) as s:
        skus = s.query(ProductSku).filter(ProductSku.product_id == pid).all()
        return [{c.name: getattr(sk, c.name) for c in sk.__table__.columns} for sk in skus]

@router.post("/api/products/skus")
async def save_sku(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        if data.get("id"):
            sk = s.query(ProductSku).filter(ProductSku.id == data["id"]).first()
            for k, v in data.items():
                if hasattr(sk, k): setattr(sk, k, v)
        else:
            sk = ProductSku(product_id=data["product_id"], name=data["name"],
                            price=data["price"], original_price=data.get("original_price"),
                            stock=data.get("stock", -1))
            s.add(sk)
        s.commit()
        return {c.name: getattr(sk, c.name) for c in sk.__table__.columns}

@router.delete("/api/products/skus/{sid}")
async def delete_sku(sid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(ProductSku).filter(ProductSku.id == sid).delete()
        s.commit()
    return {"message": "已删除"}

# 商品文件上传
@router.post("/api/admin/products/{pid}/files")
async def upload_product_file(pid: int, request: Request, file: UploadFile = File(...)):
    await require_admin(request)
    target_dir = os.path.join(config.UPLOAD_DIR, "product_files")
    os.makedirs(target_dir, exist_ok=True)
    
    content = await file.read()
    ext = os.path.splitext(file.filename)[1].lower()
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(target_dir, name)
    
    with open(path, "wb") as f:
        f.write(content)
    
    file_size = f"{len(content) / 1024:.2f} KB"
    rel_path = os.path.relpath(path, config.UPLOAD_DIR).replace("\\", "/")
    
    with Session(engine) as s:
        pf = ProductFile(
            product_id=pid,
            file_name=file.filename,
            file_path=path,
            file_size=file_size
        )
        s.add(pf)
        
        # 更新商品的文件列表
        product = s.query(Product).filter(Product.id == pid).first()
        files_list = json.loads(product.files_list or "[]")
        files_list.append({
            "id": pf.id,
            "name": file.filename,
            "size": file_size,
            "path": path,
            "url": f"/api/download/{rel_path}"
        })
        product.files_list = json.dumps(files_list, ensure_ascii=False)
        
        s.commit()
        return {"file": {c.name: getattr(pf, c.name) for c in pf.__table__.columns}, "list": files_list}

# 获取商品文件列表
@router.get("/api/admin/products/{pid}/files")
async def list_product_files(pid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        files = s.query(ProductFile).filter(ProductFile.product_id == pid).all()
        return [{"id": f.id, "file_name": f.file_name, "file_size": f.file_size, "file_path": f.file_path, "created_at": f.created_at} for f in files]

# 删除商品文件
@router.delete("/api/admin/products/{pid}/files/{fid}")
async def delete_product_file(pid: int, fid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        pf = s.query(ProductFile).filter(ProductFile.id == fid).first()
        if pf and os.path.exists(pf.file_path):
            os.remove(pf.file_path)
        
        s.query(ProductFile).filter(ProductFile.id == fid).delete()
        
        # 更新商品的文件列表
        product = s.query(Product).filter(Product.id == pid).first()
        if product.files_list:
            files_list = json.loads(product.files_list)
            files_list = [f for f in files_list if f["id"] != fid]
            product.files_list = json.dumps(files_list, ensure_ascii=False)
        
        s.commit()
        return {"message": "已删除"}

# 从temp文件夹压缩文件
@router.post("/api/admin/products/{pid}/compress-temp")
async def compress_temp_files_to_product(pid: int, request: Request, temp_files: list[dict] = None):
    await require_admin(request)
    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid).first()
        if not product:
            raise HTTPException(404, "商品不存在")
        
        temp_dir = config.TEMP_DIR
        zip_dir = os.path.join(config.UPLOAD_DIR, "zip_files")
        os.makedirs(zip_dir, exist_ok=True)
        
        # 清理文件名中的非法字符
        safe_product_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in product.name)
        zip_name = f"{safe_product_name}.zip"
        zip_path = os.path.join(zip_dir, zip_name)
        
        # 如果没有指定temp_files，就压缩整个temp文件夹
        if not temp_files:
            temp_files = []
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        temp_files.append({"temp_name": filename, "original_name": filename})
        
        if not temp_files:
            raise HTTPException(400, "没有可压缩的文件")
        
        # 生成压缩包
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for temp_file in temp_files:
                temp_file_path = os.path.join(temp_dir, temp_file.get("temp_name"))
                if os.path.exists(temp_file_path):
                    original_name = temp_file.get("original_name", temp_file.get("temp_name"))
                    zf.write(temp_file_path, original_name)
        
        # 更新商品的压缩包信息
        total_size = os.path.getsize(zip_path)
        rel_path = os.path.relpath(zip_path, config.UPLOAD_DIR)
        
        product.file_path = f"/api/download/{rel_path}"
        product.file_name = zip_name
        product.file_size = f"{total_size / 1024 / 1024:.2f} MB"
        s.commit()
        
        # 清理temp文件夹
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"清理temp文件时出错: {e}")
        
        return {
            "zip_path": product.file_path, 
            "file_name": product.file_name, 
            "file_size": product.file_size,
            "relative_path": rel_path
        }

# 生成压缩包（兼容旧版本）
@router.post("/api/admin/products/{pid}/compress")
async def compress_product_files(pid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid).first()
        files = s.query(ProductFile).filter(ProductFile.product_id == pid).all()
        
        if not files:
            raise HTTPException(400, "没有可压缩的文件")
        
        os.makedirs(os.path.join(config.UPLOAD_DIR, "zip_files"), exist_ok=True)
        
        # 清理文件名中的非法字符
        safe_product_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in product.name)
        zip_name = f"{safe_product_name}.zip"
        zip_path = os.path.join(config.UPLOAD_DIR, "zip_files", zip_name)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                if os.path.exists(f.file_path):
                    zf.write(f.file_path, f.file_name)
        
        # 更新商品的压缩包信息
        total_size = os.path.getsize(zip_path)
        rel_path = os.path.relpath(zip_path, config.UPLOAD_DIR)
        
        product.file_path = f"/api/download/{rel_path}"
        product.file_name = zip_name
        product.file_size = f"{total_size / 1024 / 1024:.2f} MB"
        s.commit()
        
        return {
            "zip_path": product.file_path, 
            "file_name": product.file_name, 
            "file_size": product.file_size,
            "relative_path": rel_path
        }

# 推荐商品管理
@router.get("/api/admin/recommends")
async def list_recommends(request: Request):
    await require_admin(request)
    with Session(engine) as s:
        recs = s.query(RecommendProduct).order_by(RecommendProduct.sort_order).all()
        result = []
        for r in recs:
            product_ids = json.loads(r.product_ids or "[]")
            products = []
            if product_ids:
                prods = s.query(Product).filter(Product.id.in_(product_ids)).all()
                products = [{
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "image_url": p.image_url
                } for p in prods]
            result.append({
                "id": r.id,
                "category_id": r.category_id,
                "category_name": r.category_name,
                "product_ids": product_ids,
                "products": products,
                "sort_order": r.sort_order
            })
        return result

# 添加/更新推荐分类
@router.post("/api/admin/recommends")
async def save_recommend(data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        if data.get("id"):
            rec = s.query(RecommendProduct).filter(RecommendProduct.id == data["id"]).first()
            rec.category_name = data.get("category_name", "")
            rec.category_id = data.get("category_id", 0)
            rec.product_ids = json.dumps(data.get("product_ids", []), ensure_ascii=False)
            rec.sort_order = data.get("sort_order", 0)
        else:
            rec = RecommendProduct(
                category_name=data.get("category_name", ""),
                category_id=data.get("category_id", 0),
                product_ids=json.dumps(data.get("product_ids", []), ensure_ascii=False),
                sort_order=data.get("sort_order", 0)
            )
            s.add(rec)
        s.commit()
        return {"id": rec.id}

# 删除推荐分类
@router.delete("/api/admin/recommends/{rid}")
async def delete_recommend(rid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(RecommendProduct).filter(RecommendProduct.id == rid).delete()
        s.commit()
        return {"message": "已删除"}

# 获取前台推荐商品
@router.get("/api/recommends")
def get_public_recommends():
    with Session(engine) as s:
        recs = s.query(RecommendProduct).order_by(RecommendProduct.sort_order).all()
        result = []
        for r in recs:
            product_ids = json.loads(r.product_ids or "[]")
            products = []
            if product_ids:
                prods = s.query(Product).filter(Product.id.in_(product_ids), Product.is_active == True).all()
                products = [{
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "display_price": get_display_price(p),
                    "original_display_price": get_original_display_price(p),
                    "image_url": p.image_url,
                    "short_description": p.short_description,
                    "is_hot": p.is_hot,
                    "is_new": p.is_new,
                    "badge": get_discount_badge(p)
                } for p in prods]
            result.append({
                "id": r.id,
                "category_name": r.category_name,
                "products": products
            })
        return result

# ========== 数据完整性校验 ==========
@router.get("/api/admin/data-integrity/issues")
async def list_integrity_issues(request: Request):
    await require_admin(request)
    return {"issues": get_open_issues(), "count": get_open_count()}

@router.post("/api/admin/data-integrity/resolve/{issue_id}")
async def resolve_integrity_issue(issue_id: str, request: Request):
    await require_admin(request)
    remaining = resolve_issue(issue_id)
    return {"remaining": remaining}

@router.get("/api/admin/data-integrity/count")
async def integrity_count(request: Request):
    await require_admin(request)
    return {"count": get_open_count()}
