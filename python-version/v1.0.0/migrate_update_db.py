"""更新数据库中的缩略图URL"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Product

engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})

with Session(engine) as s:
    p = s.query(Product).filter(Product.id == 1).first()
    if p:
        thumb_dir = os.path.join(config.SHOP_DATA_DIR, "1", "media", "video", "show_frame")
        vids = [u.strip() for u in (p.video_url or "").split(",") if u.strip()]
        thumb_files = sorted([f for f in os.listdir(thumb_dir) if f.startswith("SF_1_")]) if os.path.exists(thumb_dir) else []
        
        new_thumbs = []
        for i, vf in enumerate(vids):
            if i < len(thumb_files):
                new_thumbs.append(f"/api/image/shop/1/media/video/show_frame/{thumb_files[i]}")
            else:
                new_thumbs.append("")
        
        p.video_thumbnails = ",".join(new_thumbs)
        s.commit()
        print(f"更新了 {len(new_thumbs)} 个缩略图URL")
        print(f"video_thumbnails: {p.video_thumbnails}")
