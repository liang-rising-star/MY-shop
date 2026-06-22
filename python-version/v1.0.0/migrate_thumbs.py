"""为视频生成缩略图并修正文件名"""
import os, sys, shutil, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import config

shop_dir = os.path.join(config.SHOP_DATA_DIR, "1")
vid_dir = os.path.join(shop_dir, "media", "video", "vedio")
thumb_dir = os.path.join(shop_dir, "media", "video", "show_frame")
os.makedirs(thumb_dir, exist_ok=True)

import cv2

for f in os.listdir(vid_dir):
    if not f.endswith(('.mp4', '.webm', '.mov')):
        continue
    video_path = os.path.join(vid_dir, f)
    
    # 修正文件名：IMG_ 开头的改成 VID_
    if f.startswith("IMG_1_"):
        new_name = "VID_1_" + f.split("_1_", 1)[1]
        new_path = os.path.join(vid_dir, new_name)
        os.rename(video_path, new_path)
        video_path = new_path
        f = new_name
        print(f"  重命名: {f}")
    
    # 生成缩略图
    try:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                if max(h, w) > 200:
                    scale = 200 / max(h, w)
                    frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                sf_name = f"SF_1_{uuid.uuid4().hex}.jpg"
                sf_path = os.path.join(thumb_dir, sf_name)
                cv2.imwrite(sf_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                print(f"  缩略图: {f} -> {sf_name}")
            cap.release()
    except Exception as e:
        print(f"  错误: {f}: {e}")

print("\n完成！")
