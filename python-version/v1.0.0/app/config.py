import os, secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "Data")

if not os.path.exists(DATA_DIR):
    print(f"[警告] Data目录不存在，正在创建: {DATA_DIR}")
    os.makedirs(DATA_DIR, exist_ok=True)

def get_jwt_secret():
    secret_file = os.path.join(DATA_DIR, "jwt_secret.txt")
    if os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            return f.read().strip()
    secret = secrets.token_hex(32)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(secret_file, "w") as f:
        f.write(secret)
    return secret

class Config:
    PORT: int = int(os.getenv("PORT", "8080"))
    DATA_DIR: str = DATA_DIR
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(DATA_DIR, "system", "data_db", "shop.db"))
    JWT_SECRET: str = os.getenv("JWT_SECRET", get_jwt_secret())
    JWT_ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(DATA_DIR, "system", "others"))
    TEMP_DIR: str = os.getenv("TEMP_DIR", os.path.join(DATA_DIR, "uploads_temp"))
    SHOP_DATA_DIR: str = os.getenv("SHOP_DATA_DIR", os.path.join(DATA_DIR, "shop"))
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = os.getenv("SMTP_PORT", "587")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")

config = Config()
