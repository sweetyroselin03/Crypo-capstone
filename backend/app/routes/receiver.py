import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, Response
from app.database import db
from app.models import Transfer, ReceiverSession
from app.crypto.ciphers import CryptoEngine
from app.crypto.keywrap import KeyWrapManager
from app.crypto.excel_handler import ExcelHandler
from app.storage import get_storage
from app.utils.security import get_validated_session, log_audit_event
from app.config import Config

receiver_bp = Blueprint("receiver", __name__)

@receiver_bp.route("/transfers/<transfer_id>/password", methods=["POST"])
def verify_password(transfer_id):
    """
    Module 2: Receiver Authentication Step 2 - Password Verification
    Requires session state: QR_OK
    Unwraps AES-GCM wrapped package.
    Lockout: 5 failed attempts -> 15 min lockout.
    On success: moves to PASSWORD_OK and activates KEY_SHOWN for 30s.
    """
    session, err = get_validated_session(transfer_id)
    if err:
        return err

    # Strict state machine order check
    if session.current_state != "QR_OK":
        return jsonify({
            "error": f"Invalid workflow step. Expected state 'QR_OK', current is '{session.current_state}'"
        }), 403

    payload = request.get_json(silent=True) or {}
    password = payload.get("password", "")

    transfer = session.transfer
    wrapped_pkg = json.loads(transfer.wrapped_key_package)

    try:
        # Attempt key unwrap using PBKDF2 (200k iter) + AES-256-GCM
        unwrapped = KeyWrapManager.unwrap_keys(password, wrapped_pkg)

        # Successful verification
        session.failed_password_attempts = 0
        session.current_state = "KEY_SHOWN"
        session.key_revealed_at = datetime.now(timezone.utc)
        db.session.commit()

        # Create masked representation (only first 4 and last 4 hex chars, rest masked)
        enc_key_hex = unwrapped["encryption_key"].hex()
        masked_key = f"{enc_key_hex[:4]}••••••••••••••••••••••••{enc_key_hex[-4:]}"

        log_audit_event(
            transfer_id=transfer_id,
            event_type="PASSWORD_VERIFICATION_SUCCESS",
            success=True,
            metadata={"from_state": "QR_OK", "to_state": "KEY_SHOWN"}
        )

        return jsonify({
            "current_state": "KEY_SHOWN",
            "message": "Password verified. Temporary key revealed for 30 seconds.",
            "masked_key": masked_key,
            "algorithm": unwrapped["algorithm"],
            "timeout_seconds": Config.KEY_REVEAL_TIMEOUT_SECONDS,
            "revealed_at": session.key_revealed_at.isoformat()
        }), 200

    except ValueError:
        # Increment failed attempts
        session.failed_password_attempts += 1
        now = datetime.now(timezone.utc)

        if session.failed_password_attempts >= Config.MAX_PASSWORD_ATTEMPTS:
            lockout_time = now + timedelta(minutes=Config.LOCKOUT_DURATION_MINUTES)
            session.locked_until = lockout_time
            db.session.commit()

            log_audit_event(
                transfer_id=transfer_id,
                event_type="TRANSFER_LOCKED_PASSWORD_FAILURES",
                success=False,
                metadata={"attempt": session.failed_password_attempts, "lockout_duration_min": Config.LOCKOUT_DURATION_MINUTES}
            )

            return jsonify({
                "error": f"Too many failed password attempts. Account locked for {Config.LOCKOUT_DURATION_MINUTES} minutes.",
                "locked_until": lockout_time.isoformat(),
                "remaining_seconds": Config.LOCKOUT_DURATION_MINUTES * 60
            }), 403

        remaining_attempts = Config.MAX_PASSWORD_ATTEMPTS - session.failed_password_attempts
        db.session.commit()

        log_audit_event(
            transfer_id=transfer_id,
            event_type="PASSWORD_VERIFICATION_FAILED",
            success=False,
            metadata={"attempt": session.failed_password_attempts}
        )

        return jsonify({
            "error": "Invalid transfer password.",
            "remaining_attempts": remaining_attempts
        }), 401


@receiver_bp.route("/transfers/<transfer_id>/key-reveal", methods=["POST", "GET"])
def check_key_reveal(transfer_id):
    """
    Check key reveal timeout (30 seconds).
    If 30 seconds have elapsed, transition automatically to EYE_ENROLLMENT ready.
    """
    session, err = get_validated_session(transfer_id)
    if err:
        return err

    if session.current_state not in ["KEY_SHOWN", "PASSWORD_OK"]:
        return jsonify({
            "error": f"Invalid workflow transition. Current state is '{session.current_state}'"
        }), 403

    now = datetime.now(timezone.utc)
    revealed_at = session.key_revealed_at.replace(tzinfo=timezone.utc) if session.key_revealed_at else now
    elapsed_sec = (now - revealed_at).total_seconds()
    remaining_sec = max(0, int(Config.KEY_REVEAL_TIMEOUT_SECONDS - elapsed_sec))

    if remaining_sec == 0:
        # 30-second reveal period has ended
        return jsonify({
            "current_state": session.current_state,
            "expired": True,
            "remaining_seconds": 0,
            "message": "Temporary key reveal window has closed. Proceed to eye enrollment."
        }), 200

    return jsonify({
        "current_state": "KEY_SHOWN",
        "expired": False,
        "remaining_seconds": remaining_sec,
        "timeout_seconds": Config.KEY_REVEAL_TIMEOUT_SECONDS
    }), 200


@receiver_bp.route("/transfers/<transfer_id>/decrypt", methods=["POST"])
def decrypt_file(transfer_id):
    """
    Module 3: Secure Decryption and Data View
    Strictly requires session state: EYE_VERIFIED
    1. Verify session state is EYE_VERIFIED (returns 403 on skipped steps).
    2. Check transfer not locked or expired.
    3. Retrieve password from request body to unwrap keys.
    4. Verify HMAC-SHA256 with constant-time comparison.
    5. Decrypt CSV bytes using selected cipher and unpad PKCS7.
    6. Transition state to DATA_VIEW.
    7. Convert CSV to structured records for UI table viewing.
    """
    session, err = get_validated_session(transfer_id)
    if err:
        return err

    # Strict server-enforced state check
    if session.current_state != "EYE_VERIFIED":
        log_audit_event(
            transfer_id=transfer_id,
            event_type="UNAUTHORIZED_DECRYPTION_ATTEMPT_BLOCKED",
            success=False,
            metadata={"current_state": session.current_state}
        )
        return jsonify({
            "error": f"Decryption blocked: Biometric eye verification required. Current state is '{session.current_state}', expected 'EYE_VERIFIED'"
        }), 403

    payload = request.get_json(silent=True) or {}
    password = payload.get("password")

    if not password:
        return jsonify({"error": "Transfer password required to unwrap encryption keys"}), 400

    transfer = session.transfer
    wrapped_pkg = json.loads(transfer.wrapped_key_package)

    try:
        # Unwrap keys
        unwrapped = KeyWrapManager.unwrap_keys(password, wrapped_pkg)
    except ValueError:
        return jsonify({"error": "Decryption failed: invalid password"}), 401

    # Retrieve encrypted package from storage
    storage = get_storage()
    pkg_bytes = storage.get(transfer.encrypted_storage_key)
    if not pkg_bytes:
        return jsonify({"error": "Encrypted package not found in storage"}), 404

    try:
        encrypted_pkg = json.loads(pkg_bytes.decode("utf-8"))
    except Exception:
        return jsonify({"error": "Corrupted encrypted package"}), 500

    # Step 6: Verify HMAC-SHA256 with constant-time comparison
    version = encrypted_pkg.get("version", "1.0")
    iv_b64 = encrypted_pkg.get("iv", "")
    ciphertext_b64 = encrypted_pkg.get("ciphertext", "")
    hmac_tag = encrypted_pkg.get("hmac_tag", "")
    algorithm = encrypted_pkg.get("algorithm", "")

    hmac_valid = CryptoEngine.verify_hmac(
        hmac_key=unwrapped["hmac_key"],
        expected_hmac_hex=hmac_tag,
        version=version,
        transfer_id=transfer_id,
        algorithm=algorithm,
        iv_b64=iv_b64,
        ciphertext_b64=ciphertext_b64
    )

    if not hmac_valid:
        log_audit_event(
            transfer_id=transfer_id,
            event_type="HMAC_TAMPER_DETECTED",
            success=False,
            metadata={"algorithm": algorithm}
        )
        return jsonify({
            "error": "Integrity check failed: Encrypted data has been tampered with or corrupted. HMAC verification failed."
        }), 400

    # Step 7: Decrypt ciphertext
    import base64
    ciphertext = base64.b64decode(ciphertext_b64)
    iv = base64.b64decode(iv_b64)

    try:
        decrypted_csv_bytes = CryptoEngine.decrypt(
            ciphertext=ciphertext,
            algorithm=algorithm,
            key=unwrapped["encryption_key"],
            iv=iv
        )
    except Exception:
        return jsonify({"error": "Decryption failed: corrupted data or invalid cipher parameters"}), 400

    # Transition state to DATA_VIEW
    session.current_state = "DATA_VIEW"
    transfer.status = "COMPLETED"
    db.session.commit()

    # Convert CSV into structured records for frontend table
    structured_data = ExcelHandler.csv_to_structured_data(decrypted_csv_bytes)

    log_audit_event(
        transfer_id=transfer_id,
        event_type="DECRYPTION_SUCCESS",
        success=True,
        metadata={
            "to_state": "DATA_VIEW",
            "algorithm": algorithm,
            "rows_recovered": structured_data["total_rows"]
        }
    )

    return jsonify({
        "current_state": "DATA_VIEW",
        "message": "File successfully decrypted and verified via HMAC-SHA256.",
        "filename": transfer.original_filename,
        "algorithm": algorithm,
        "structured_data": structured_data
    }), 200


@receiver_bp.route("/transfers/<transfer_id>/download-csv", methods=["POST"])
def download_decrypted_csv(transfer_id):
    """Download decrypted CSV file once session is in DATA_VIEW."""
    session, err = get_validated_session(transfer_id)
    if err:
        return err

    if session.current_state != "DATA_VIEW":
        return jsonify({"error": "Decryption required before download"}), 403

    payload = request.get_json(silent=True) or {}
    password = payload.get("password")
    if not password:
        return jsonify({"error": "Password required"}), 400

    transfer = session.transfer
    wrapped_pkg = json.loads(transfer.wrapped_key_package)
    unwrapped = KeyWrapManager.unwrap_keys(password, wrapped_pkg)

    storage = get_storage()
    pkg_bytes = storage.get(transfer.encrypted_storage_key)
    encrypted_pkg = json.loads(pkg_bytes.decode("utf-8"))

    import base64
    ciphertext = base64.b64decode(encrypted_pkg["ciphertext"])
    iv = base64.b64decode(encrypted_pkg["iv"])
    csv_bytes = CryptoEngine.decrypt(ciphertext, encrypted_pkg["algorithm"], unwrapped["encryption_key"], iv)

    base_name = transfer.original_filename.rsplit(".", 1)[0]
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={base_name}_decrypted.csv"}
    )


@receiver_bp.route("/transfers/<transfer_id>/download-excel", methods=["POST"])
def download_decrypted_excel(transfer_id):
    """Download reconstructed Excel workbook from decrypted CSV."""
    session, err = get_validated_session(transfer_id)
    if err:
        return err

    if session.current_state != "DATA_VIEW":
        return jsonify({"error": "Decryption required before download"}), 403

    payload = request.get_json(silent=True) or {}
    password = payload.get("password")
    if not password:
        return jsonify({"error": "Password required"}), 400

    transfer = session.transfer
    wrapped_pkg = json.loads(transfer.wrapped_key_package)
    unwrapped = KeyWrapManager.unwrap_keys(password, wrapped_pkg)

    storage = get_storage()
    pkg_bytes = storage.get(transfer.encrypted_storage_key)
    encrypted_pkg = json.loads(pkg_bytes.decode("utf-8"))

    import base64
    ciphertext = base64.b64decode(encrypted_pkg["ciphertext"])
    iv = base64.b64decode(encrypted_pkg["iv"])
    csv_bytes = CryptoEngine.decrypt(ciphertext, encrypted_pkg["algorithm"], unwrapped["encryption_key"], iv)
    excel_bytes = ExcelHandler.csv_to_excel(csv_bytes)

    base_name = transfer.original_filename.rsplit(".", 1)[0]
    return Response(
        excel_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={base_name}_recovered.xlsx"}
    )
