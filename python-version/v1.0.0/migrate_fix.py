"""修正迁移：把误放到image目录的mp4文件挪到video目录"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import config

shop_dir = os.path.join(config.SHOP_DATA_DIR, "1")
img_dir = os.path.join(shop_dir, "media", "image")
vid_dir = os.path.join(shop_dir, "media", "video", "vedio")

video_exts = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'}

moved = 0
for f in os.listdir(img_dir):
    ext = os.path.splitext(f)[1].lower()
    if ext in video_exts:
        src = os.path.join(img_dir, f)
        dst = os.path.join(vid_dir, f)
        shutil.move(src, dst)
        print(f"  移动: image/{f} -> vedio/{f}")
        moved += 1

print(f"\n共移动 {moved} 个视频文件到 video/vedio/ 目录")
