import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'crypto_cp.db')

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(String(64), primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    cipher_type = Column(String(32), nullable=False)  # 'AES' or 'Blowfish'
    encrypted_file_path = Column(String(512), nullable=False)
    password_hash = Column(String(256), nullable=False)
    password_salt = Column(String(256), nullable=False)
    qr_payload = Column(Text, nullable=False)
    qr_image_path = Column(String(512), nullable=False)

    # Security Lockouts
    failed_password_attempts = Column(Integer, default=0)
    password_locked_until = Column(Float, default=0.0)  # Epoch timestamp
    failed_eye_attempts = Column(Integer, default=0)
    eye_locked_until = Column(Float, default=0.0)       # Epoch timestamp

    # Performance Benchmark
    enc_time_ms = Column(Float, default=0.0)
    throughput_kb_s = Column(Float, default=0.0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BiometricTemplate(Base):
    __tablename__ = "biometric_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transfer_id = Column(String(64), index=True, nullable=False)
    # Stored encrypted at rest using AES-GCM with server secret
    encrypted_template = Column(LargeBinary, nullable=False)
    nonce = Column(LargeBinary, nullable=False)
    sample_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transfer_id = Column(String(64), index=True, nullable=True)
    step = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)  # 'SUCCESS', 'FAILURE', 'LOCKED', 'OUT_OF_ORDER'
    details = Column(Text, nullable=False)       # NO secrets or keys
    ip_address = Column(String(64), default="127.0.0.1")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)


def log_audit(step: str, status: str, details: str, transfer_id: str = None, ip_address: str = "127.0.0.1"):
    """
    Appends an audit log record. Ensures secrets are never logged.
    """
    db = SessionLocal()
    try:
        entry = AuditLog(
            transfer_id=transfer_id,
            step=step,
            status=status,
            details=details,
            ip_address=ip_address
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging audit: {e}")
    finally:
        db.close()

