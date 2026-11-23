import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "capstone-super-secret-key-csa5106-2026")
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Database: SQLite locally, PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'crypto_capstone.db'}"
    )
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

    # Storage
    STORAGE_TYPE = os.environ.get("STORAGE_TYPE", "local")  # 'local' or 's3'
    LOCAL_STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", str(BASE_DIR / "storage")))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE_BYTES", 16 * 1024 * 1024))  # 16 MB max

    # Biometrics & Liveness
    EYE_SIMILARITY_THRESHOLD = float(os.environ.get("EYE_SIMILARITY_THRESHOLD", 0.90))
    BLINK_EAR_CLOSE_THRESHOLD = float(os.environ.get("BLINK_EAR_CLOSE_THRESHOLD", 0.17))
    BLINK_EAR_OPEN_THRESHOLD = float(os.environ.get("BLINK_EAR_OPEN_THRESHOLD", 0.22))

    # Security Lockouts & Timeouts
    MAX_PASSWORD_ATTEMPTS = int(os.environ.get("MAX_PASSWORD_ATTEMPTS", 5))
    MAX_EYE_ATTEMPTS = int(os.environ.get("MAX_EYE_ATTEMPTS", 3))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get("LOCKOUT_DURATION_MINUTES", 15))
    SESSION_EXPIRY_MINUTES = int(os.environ.get("SESSION_EXPIRY_MINUTES", 60))
    KEY_REVEAL_TIMEOUT_SECONDS = int(os.environ.get("KEY_REVEAL_TIMEOUT_SECONDS", 30))
