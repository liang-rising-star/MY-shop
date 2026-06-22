"""迁移旧文件到新的 Data/shop/<pid>/ 目录结构"""
import os, sys, shutil, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.models import Product

engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})

def migrate():
    with Session(engine) as s:
        products = s.query(Product).all()
        for p in products:
            pid = p.id
            print(f"\n=== 商品 {pid}: {p.name} ===")
            
            shop_dir = os.path.join(config.SHOP_DATA_DIR, str(pid))
            img_dir = os.path.join(shop_dir, "media", "image")
            vid_dir = os.path.join(shop_dir, "media", "video", "vedio")
            thumb_dir = os.path.join(shop_dir, "media", "video", "show_frame")
            for d in [img_dir, vid_dir, thumb_dir]:
                os.makedirs(d, exist_ok=True)
            
            old_images = [u.strip() for u in (p.images or "").split(",") if u.strip()]
            old_video_url = p.video_url or ""
            old_videos = [u.strip() for u in old_video_url.split(",") if u.strip()]
            old_thumbnails = [u.strip() for u in (p.video_thumbnails or "").split(",") if u.strip()]
            
            new_images = []
            new_videos = []
            new_thumbs = []
            
            img_counter = 0
            for url in old_images:
                old_path = os.path.join(config.UPLOAD_DIR, url.replace("/api/image/", ""))
                if not os.path.exists(old_path):
                    continue
                ext = os.path.splitext(url)[1].lower()
                img_counter += 1
                new_name = f"IMG_{pid}_{uuid.uuid4().hex}{ext}"
                new_path = os.path.join(img_dir, new_name)
                shutil.copy2(old_path, new_path)
                new_url = f"/api/image/shop/{pid}/media/image/{new_name}"
                new_images.append(new_url)
                print(f"  图片: {url} -> {new_url}")
            
            vid_counter = 0
            for i, url in enumerate(old_videos):
                old_path = os.path.join(config.UPLOAD_DIR, url.replace("/api/image/", ""))
                if not os.path.exists(old_path):
                    continue
                ext = os.path.splitext(url)[1].lower()
                vid_counter += 1
                new_name = f"VID_{pid}_{uuid.uuid4().hex}{ext}"
                new_path = os.path.join(vid_dir, new_name)
                shutil.copy2(old_path, new_path)
                new_url = f"/api/image/shop/{pid}/media/video/vedio/{new_name}"
                new_videos.append(new_url)
                print(f"  视频: {url} -> {new_url}")
                
                thumb_url = old_thumbnails[i] if i < len(old_thumbnails) else ""
                if thumb_url:
                    old_thumb_path = os.path.join(config.UPLOAD_DIR, thumb_url.replace("/api/image/", ""))
                    if os.path.exists(old_thumb_path):
                        sf_name = f"SF_{pid}_{uuid.uuid4().hex}.jpg"
                        sf_path = os.path.join(thumb_dir, sf_name)
                        shutil.copy2(old_thumb_path, sf_path)
                        sf_url = f"/api/image/shop/{pid}/media/video/show_frame/{sf_name}"
                        new_thumbs.append(sf_url)
                        print(f"  缩略图: {thumb_url} -> {sf_url}")
                    else:
                        new_thumbs.append("")
                else:
                    new_thumbs.append("")
            
            if new_images or new_videos:
                new_images_str = ",".join(new_images) if new_images else ""
                new_videos_str = ",".join(new_videos) if new_videos else ""
                new_thumbs_str = ",".join(new_thumbs) if new_thumbs else ""
                new_image_url = new_images[0] if new_images else (new_videos[0] if new_videos else "")
                
                p.images = new_images_str
                p.video_url = new_videos_str
                p.video_thumbnails = new_thumbs_str
                if new_image_url:
                    p.image_url = new_image_url
                print(f"  数据库已更新")
            
            s.commit()
    print("\n迁移完成！")

if __name__ == "__main__":
    migrate()
