import hashlib
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from flask import request, jsonify
from app.database import db
from app.models import ReceiverSession, AuditLog, Transfer
from app.config import Config

# Strict state machine flow:
# QR_OK -> PASSWORD_OK -> KEY_SHOWN -> EYE_ENROLLED -> EYE_VERIFIED -> DATA_VIEW
VALID_STATES = [
    "QR_OK",
    "PASSWORD_OK",
    "KEY_SHOWN",
    "EYE_ENROLLED",
    "EYE_VERIFIED",
    "DATA_VIEW"
]

def generate_session_token() -> Tuple[str, str]:
    """Generate raw token for client and SHA-256 hash for database."""
    token = secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash

def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def log_audit_event(transfer_id: Optional[str], event_type: str, success: bool = True, metadata: Optional[Dict[str, Any]] = None):
    """
    Log security event to audit_logs table with strictly sanitized metadata.
    Never logs passwords, encryption keys, IVs, biometric vectors, or file contents.
    """
    sanitized = {}
    if metadata:
        # Whitelist safe keys only
        safe_keys = {
            "algorithm", "filename", "file_size_kb", "ip", "attempt",
            "state", "from_state", "to_state", "similarity_score",
            "liveness_passed", "lockout_duration_min", "reason"
        }
        for k, v in metadata.items():
            if k in safe_keys:
                sanitized[k] = v

    try:
        log_entry = AuditLog(
            id=secrets.token_hex(16),
            transfer_id=transfer_id,
            event_type=event_type,
            event_timestamp=datetime.now(timezone.utc),
            success=success,
            sanitized_metadata=json.dumps(sanitized) if sanitized else None
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

def get_validated_session(transfer_id: str) -> Tuple[Optional[ReceiverSession], Optional[Tuple[Any, int]]]:
    """
    Extract session token from Authorization: Bearer <token> or X-Session-Token header,
    validate existence, expiration, and transfer lockouts.
    Returns (session, None) on success or (None, (error_response, status_code)) on failure.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        token = request.headers.get("X-Session-Token")

    if not token:
        return None, (jsonify({"error": "Missing session authentication token"}), 401)

    token_hash = get_token_hash(token)
    session = ReceiverSession.query.filter_by(transfer_id=transfer_id, session_token_hash=token_hash).first()

    if not session:
        return None, (jsonify({"error": "Invalid or expired session"}), 401)

    now = datetime.now(timezone.utc)

    # Check session expiration
    if session.expires_at.replace(tzinfo=timezone.utc) < now:
        return None, (jsonify({"error": "Session expired. Please re-scan QR code."}), 401)

    # Check lockout
    if session.locked_until and session.locked_until.replace(tzinfo=timezone.utc) > now:
        remaining_sec = int((session.locked_until.replace(tzinfo=timezone.utc) - now).total_seconds())
        remaining_min = max(1, remaining_sec // 60)
        return None, (jsonify({
            "error": f"Security lockout active. Try again in {remaining_min} minute(s).",
            "locked_until": session.locked_until.isoformat(),
            "remaining_seconds": remaining_sec
        }), 403)

    return session, None
