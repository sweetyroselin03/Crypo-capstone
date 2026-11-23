from flask import Blueprint, jsonify
from app.models import Transfer, ReceiverSession, AuditLog
from app.database import db

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Crypto Capstone API",
        "course": "CSA5106 - Cryptography and Network Security",
        "version": "1.0.0"
    }), 200

@health_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """Aggregate dashboard metrics for the Overview page."""
    total_transfers = Transfer.query.count()
    completed_decryptions = ReceiverSession.query.filter_by(current_state="DATA_VIEW").count()
    failed_passwords = AuditLog.query.filter_by(event_type="PASSWORD_VERIFICATION_FAILED").count()
    failed_biometrics = AuditLog.query.filter_by(event_type="EYE_VERIFICATION_FAILED").count()

    aes_count = Transfer.query.filter_by(algorithm="AES-128-CBC").count()
    bf_count = Transfer.query.filter_by(algorithm="Blowfish-CBC").count()

    recent_logs = AuditLog.query.order_by(AuditLog.event_timestamp.desc()).limit(8).all()

    return jsonify({
        "total_transfers": total_transfers,
        "completed_decryptions": completed_decryptions,
        "failed_attempts": failed_passwords + failed_biometrics,
        "failed_passwords": failed_passwords,
        "failed_biometrics": failed_biometrics,
        "algorithms": {
            "AES-128-CBC": aes_count,
            "Blowfish-CBC": bf_count
        },
        "recent_activity": [log.to_dict() for log in recent_logs]
    }), 200
