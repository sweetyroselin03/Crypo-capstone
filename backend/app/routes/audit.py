from flask import Blueprint, jsonify, request
from app.models import AuditLog

audit_bp = Blueprint("audit", __name__)

@audit_bp.route("/audit-logs", methods=["GET"])
def get_audit_logs():
    """
    Return sanitized audit logs.
    Guaranteed: NO passwords, encryption keys, IVs, or biometric templates are logged.
    """
    limit = min(int(request.args.get("limit", 50)), 100)
    transfer_id = request.args.get("transfer_id")

    query = AuditLog.query
    if transfer_id:
        query = query.filter_by(transfer_id=transfer_id)

    logs = query.order_by(AuditLog.event_timestamp.desc()).limit(limit).all()
    return jsonify([log.to_dict() for log in logs]), 200
