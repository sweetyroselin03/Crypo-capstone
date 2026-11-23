from datetime import datetime, timezone
import json
from app.database import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Transfer(db.Model):
    __tablename__ = "transfers"

    id = db.Column(db.String(36), primary_key=True)  # UUID or transfer ID
    sender_id = db.Column(db.String(36), nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    encrypted_storage_key = db.Column(db.String(255), nullable=False)
    algorithm = db.Column(db.String(32), nullable=False)  # 'AES-128-CBC' or 'Blowfish-CBC'
    wrapped_key_package = db.Column(db.Text, nullable=False)  # JSON string of wrapped AES-GCM blob
    salt = db.Column(db.String(64), nullable=False)  # Hex-encoded PBKDF2 salt
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(32), default="ACTIVE", nullable=False)  # ACTIVE, COMPLETED, EXPIRED, LOCKED

    sessions = db.relationship("ReceiverSession", backref="transfer", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", backref="transfer", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ReceiverSession(db.Model):
    __tablename__ = "receiver_sessions"

    id = db.Column(db.String(36), primary_key=True)  # Session ID
    transfer_id = db.Column(db.String(36), db.ForeignKey("transfers.id"), nullable=False, index=True)
    session_token_hash = db.Column(db.String(128), nullable=False, index=True)
    current_state = db.Column(db.String(32), default="QR_OK", nullable=False)
    failed_password_attempts = db.Column(db.Integer, default=0, nullable=False)
    failed_eye_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Temporary cached revealed key (masked/encrypted in memory/session, valid only during KEY_SHOWN for 30s)
    key_revealed_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BiometricTemplate(db.Model):
    __tablename__ = "biometric_templates"

    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, index=True)
    encrypted_template = db.Column(db.Text, nullable=False)  # Encrypted/hashed feature vector JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True)
    transfer_id = db.Column(db.String(36), db.ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    event_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    success = db.Column(db.Boolean, default=True, nullable=False)
    sanitized_metadata = db.Column(db.Text, nullable=True)  # JSON formatted sanitized logs (NO secrets)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        meta = {}
        if self.sanitized_metadata:
            try:
                meta = json.loads(self.sanitized_metadata)
            except Exception:
                meta = {"raw": self.sanitized_metadata}
        return {
            "id": self.id,
            "transfer_id": self.transfer_id,
            "event_type": self.event_type,
            "event_timestamp": self.event_timestamp.isoformat() if self.event_timestamp else None,
            "success": self.success,
            "metadata": meta,
        }


class Benchmark(db.Model):
    __tablename__ = "benchmarks"

    id = db.Column(db.String(36), primary_key=True)
    algorithm = db.Column(db.String(32), nullable=False)
    file_size_kb = db.Column(db.Float, nullable=False)
    encryption_time_ms = db.Column(db.Float, nullable=False)
    decryption_time_ms = db.Column(db.Float, nullable=False)
    throughput_kbps = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "algorithm": self.algorithm,
            "file_size_kb": round(self.file_size_kb, 2),
            "encryption_time_ms": round(self.encryption_time_ms, 3),
            "decryption_time_ms": round(self.decryption_time_ms, 3),
            "throughput_kbps": round(self.throughput_kbps, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
