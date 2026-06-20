from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from app.database import engine
from app.models import Product, ProductCategory, CardKey, BlindBoxPool, ProductSku, RecommendProduct, ProductFile, AppSetting
from app.auth import require_admin
from app.config import config
import os, uuid, shutil, datetime, json, zipfile

router = APIRouter()

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
        return {c.name: getattr(p, c.name) for c in p.__table__.columns}

@router.delete("/api/admin/products/{pid}")
async def delete_product(pid: int, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        sold_keys = s.query(CardKey).filter(CardKey.product_id == pid, CardKey.status == "sold").count()
        if sold_keys > 0:
            raise HTTPException(400, f"无法删除，该商品已有 {sold_keys} 个卡密已售出")
        # 获取商品信息用于删除文件
        product = s.query(Product).filter(Product.id == pid).first()
        if product:
            # 删除图片/视频文件
            import glob as globmod
            if product.images:
                for img in product.images.split(","):
                    img = img.strip()
                    if img and img.startswith("/api/image/"):
                        file_path = os.path.join(config.UPLOAD_DIR, img.replace("/api/image/", ""))
                        if os.path.exists(file_path):
                            try: os.remove(file_path)
                            except: pass
            if product.video_url and product.video_url.startswith("/api/image/"):
                file_path = os.path.join(config.UPLOAD_DIR, product.video_url.replace("/api/image/", ""))
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
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
    return {"message": "已删除"}

@router.delete("/api/admin/products/{pid}/delete-file")
async def delete_product_file_by_url(pid: int, data: dict, request: Request):
    await require_admin(request)
    file_url = data.get("file", "")
    if file_url and file_url.startswith("/api/image/"):
        file_path = os.path.join(config.UPLOAD_DIR, file_url.replace("/api/image/", ""))
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
    return {"message": "已删除"}

@router.put("/api/admin/products/{pid}/blindbox")
async def update_pool(pid: int, data: dict, request: Request):
    await require_admin(request)
    with Session(engine) as s:
        s.query(BlindBoxPool).filter(BlindBoxPool.product_id == pid).delete()
        for e in data["entries"]:
            s.add(BlindBoxPool(product_id=pid, prize_id=e["prize_id"], probability=e["probability"]))
        s.commit()
    return {"message": "奖池已更新"}

@router.post("/api/admin/upload")
async def upload_file(request: Request, file: UploadFile = File(...), file_type: str = Form(default="image")):
    await require_admin(request)
    
    # 根据文件类型确定存储位置
    if file_type == "logo":
        target_dir = os.path.join(config.UPLOAD_DIR, "images", "logos")
    elif file_type == "product_image":
        target_dir = os.path.join(config.UPLOAD_DIR, "images", "products")
    else:  # default to other images
        target_dir = os.path.join(config.UPLOAD_DIR, "images", "others")
    
    os.makedirs(target_dir, exist_ok=True)
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp', '.ico', '.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'}
    
    # 从系统设置读取上传大小限制
    with Session(engine) as s:
        setting = s.query(AppSetting).filter(AppSetting.key == "config_upload_max_size").first()
        max_file_size = (int(setting.value) if setting else 1024) * 1024 * 1024  # MB转bytes
    
    # 获取文件名和扩展名
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()
    
    # 检查扩展名
    if ext not in allowed_extensions:
        error_msg = f"不支持的文件类型: '{ext}' (文件名: {filename})，允许的类型: {', '.join(sorted(allowed_extensions))}"
        print(f"[Upload Error] {error_msg}")
        raise HTTPException(400, error_msg)
    
    # 读取文件内容
    try:
        content = await file.read()
    except Exception as e:
        error_msg = f"读取文件失败: {str(e)}"
        print(f"[Upload Error] {error_msg}")
        raise HTTPException(400, error_msg)
    
    # 检查文件大小
    if len(content) > max_file_size:
        error_msg = f"文件大小超过限制(最大{max_file_size//1024//1024}MB)，当前大小: {len(content) / 1024 / 1024:.1f}MB"
        print(f"[Upload Error] {error_msg}")
        raise HTTPException(400, error_msg)
    
    # 生成文件名
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(target_dir, name)
    
    # 保存文件
    with open(path, "wb") as f:
        f.write(content)
    
    # 计算相对路径用于API访问
    rel_path = os.path.relpath(path, config.UPLOAD_DIR).replace("\\", "/").replace("\\", "/")
    
    # 视频自动生成缩略图
    thumb_url = ""
    if ext in ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'):
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ret, frame = cap.read()
                if ret:
                    thumb_name = f"{uuid.uuid4().hex}.jpg"
                    thumb_path = os.path.join(target_dir, thumb_name)
                    cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    thumb_rel = os.path.relpath(thumb_path, config.UPLOAD_DIR).replace("\\", "/")
                    thumb_url = f"/api/image/{thumb_rel}"
                cap.release()
        except Exception as e:
            print(f"[Thumbnail Error] {e}")
    
    print(f"[Upload Success] {filename} -> {rel_path}")
    return {
        "url": f"/api/image/{rel_path}", 
        "path": path,
        "relative_path": rel_path,
        "thumbnail": thumb_url
    }

@router.get("/api/admin/products/{pid}/thumbnail")
async def generate_video_thumbnail(pid: int, request: Request):
    """为视频生成缩略图"""
    await require_admin(request)
    with Session(engine) as s:
        product = s.query(Product).filter(Product.id == pid).first()
        if not product:
            raise HTTPException(404, "商品不存在")
        video_url = product.video_url or ""
        if not video_url:
            raise HTTPException(400, "该商品没有视频")
        video_path = os.path.join(config.UPLOAD_DIR, video_url.replace("/api/image/", ""))
        if not os.path.exists(video_path):
            raise HTTPException(404, "视频文件不存在")
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
                ret, frame = cap.read()
                if ret:
                    thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
                    thumb_dir = os.path.join(config.UPLOAD_DIR, "images", "others")
                    os.makedirs(thumb_dir, exist_ok=True)
                    thumb_path = os.path.join(thumb_dir, thumb_name)
                    cv2.imwrite(thumb_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    cap.release()
                    thumb_rel = os.path.relpath(thumb_path, config.UPLOAD_DIR).replace("\\", "/")
                    return {"thumbnail": f"/api/image/{thumb_rel}"}
                cap.release()
            raise HTTPException(500, "无法读取视频帧")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"生成缩略图失败: {str(e)}")

# 批量上传商品文件（先存到temp）
@router.post("/api/admin/products/{pid}/upload-files")
async def upload_multiple_files(pid: int, request: Request, files: list[UploadFile] = File(...)):
    await require_admin(request)
    
    # 确保temp目录存在
    temp_dir = os.path.join(config.UPLOAD_DIR, "temp")
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
    
    temp_dir = os.path.join(config.UPLOAD_DIR, "temp")
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
        
        temp_dir = os.path.join(config.UPLOAD_DIR, "temp")
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
