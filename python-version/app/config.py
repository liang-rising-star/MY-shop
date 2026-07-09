import os, secrets

def get_jwt_secret():
    secret_file = "jwt_secret.txt"
    if os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            return f.read().strip()
    secret = secrets.token_hex(32)
    with open(secret_file, "w") as f:
        f.write(secret)
    return secret

class Config:
    PORT: int = int(os.getenv("PORT", "8080"))
    DB_PATH: str = os.getenv("DB_PATH", "shop.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", get_jwt_secret())
    JWT_ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")

config = Config()
