from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import config

engine = create_engine(f"sqlite:///{config.DB_PATH}", connect_args={"check_same_thread": False})

class Base(DeclarativeBase):
    pass

def init_db():
    import app.models
    Base.metadata.create_all(bind=engine)
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cur.fetchall()]
    missing = {
        'uuid': 'VARCHAR(36)',
        'is_super_admin': 'BOOLEAN DEFAULT 0',
        'admin_permissions': 'TEXT DEFAULT ""',
        'status': 'VARCHAR(20) DEFAULT "normal"',
        'alipay_account': 'VARCHAR(100) DEFAULT ""',
        'wechat_account': 'VARCHAR(100) DEFAULT ""',
        'wallet_address': 'VARCHAR(200) DEFAULT ""',
        'last_login_ip': 'VARCHAR(50) DEFAULT ""',
        'last_login_time': 'DATETIME',
    }
    for col, typ in missing.items():
        if col not in columns:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
    conn.commit()
    conn.close()
    from sqlalchemy.orm import Session
    from app.models import User
    with Session(engine) as s:
        for u in s.query(User).filter(User.uuid == None).all():
            if u.is_super_admin:
                u.uuid = "0"
            else:
                max_uuid = s.query(User.uuid).filter(User.uuid != None).order_by(User.id.desc()).first()
                try:
                    next_uuid = int(max_uuid[0]) + 1 if max_uuid and max_uuid[0] and max_uuid[0].isdigit() else 1
                except:
                    next_uuid = 1
                u.uuid = str(next_uuid)
        s.commit()
