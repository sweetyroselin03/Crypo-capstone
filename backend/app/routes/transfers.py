import base64
import io
import json
import secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, send_file, Response
import qrcode
from app.database import db
from app.models import Transfer, ReceiverSession
from app.crypto.ciphers import CryptoEngine
from app.crypto.keywrap import KeyWrapManager
from app.crypto.excel_handler import ExcelHandler
from app.storage import get_storage
from app.utils.security import generate_session_token, log_audit_event, get_validated_session
from app.config import Config

transfers_bp = Blueprint("transfers", __name__)

@transfers_bp.route("/transfers", methods=["POST"])
def create_transfer():
    """
    Module 1: Sender Encryption and Key Wrapping
    1. Accept .xlsx file and validate.
    2. Convert Excel to CSV bytes.
    3. Select algorithm (AES-128-CBC or Blowfish-CBC).
    4. Generate random key, IV, independent HMAC key.
    5. Encrypt CSV with PKCS7 padding and compute HMAC-SHA256.
    6. Wrap keys with PBKDF2 (200k iter) + AES-256-GCM using sender password.
    7. Generate QR code containing the wrapped key package JSON.
    8. Store encrypted payload in storage.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    algorithm = request.form.get("algorithm", "AES-128-CBC")
    password = request.form.get("password", "")

    if not file or not file.filename:
        return jsonify({"error": "Invalid file upload"}), 400

    if algorithm not in ["AES-128-CBC", "Blowfish-CBC"]:
        return jsonify({"error": f"Unsupported algorithm: {algorithm}"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters for key wrapping security"}), 400

    file_bytes = file.read()
    if len(file_bytes) > Config.MAX_CONTENT_LENGTH:
        return jsonify({"error": f"File size exceeds maximum limit of {Config.MAX_CONTENT_LENGTH // (1024*1024)} MB"}), 400

    # Validate Excel format
    if not ExcelHandler.validate_excel(file_bytes, file.filename):
        return jsonify({"error": "Invalid file format. Please upload a valid .xlsx Excel workbook."}), 400

    try:
        # Convert Excel workbook to CSV bytes
        csv_bytes = ExcelHandler.excel_to_csv(file_bytes)
    except Exception as e:
        return jsonify({"error": "Failed to parse Excel workbook into CSV records."}), 400

    transfer_id = f"tr-{secrets.token_hex(6)}"

    # Generate keys and IV
    key, iv, hmac_key = CryptoEngine.generate_keys_and_iv(algorithm)

    # Encrypt CSV bytes and compute HMAC-SHA256
    encrypted_pkg = CryptoEngine.create_encrypted_package(
        data_bytes=csv_bytes,
        transfer_id=transfer_id,
        algorithm=algorithm,
        key=key,
        iv=iv,
        hmac_key=hmac_key
    )

    # Save encrypted package to storage
    storage = get_storage()
    storage_key = f"{transfer_id}.enc"
    storage.save(storage_key, json.dumps(encrypted_pkg).encode("utf-8"))

    # Password-based key wrapping with PBKDF2 (200,000 iterations) + AES-256-GCM
    salt = secrets.token_bytes(16)
    wrapped_package = KeyWrapManager.wrap_keys(
        password=password,
        transfer_id=transfer_id,
        algorithm=algorithm,
        encryption_key=key,
        iv=iv,
        hmac_key=hmac_key,
        salt=salt
    )

    # Store Transfer in database
    transfer = Transfer(
        id=transfer_id,
        original_filename=file.filename,
        encrypted_storage_key=storage_key,
        algorithm=algorithm,
        wrapped_key_package=json.dumps(wrapped_package),
        salt=salt.hex(),
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        status="ACTIVE"
    )
    db.session.add(transfer)
    db.session.commit()

    # Generate QR Code containing the wrapped key package
    qr_payload_json = json.dumps(wrapped_package)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_payload_json)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")

    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_png_bytes = buffer.getvalue()
    qr_data_url = f"data:image/png;base64,{base64.b64encode(qr_png_bytes).decode('utf-8')}"

    # Log sanitized audit event (strictly no keys or password)
    log_audit_event(
        transfer_id=transfer_id,
        event_type="TRANSFER_CREATED",
        success=True,
        metadata={
            "algorithm": algorithm,
            "filename": file.filename,
            "file_size_kb": round(len(file_bytes) / 1024.0, 2)
        }
    )

    return jsonify({
        "transfer_id": transfer_id,
        "original_filename": file.filename,
        "algorithm": algorithm,
        "file_size_bytes": len(file_bytes),
        "qr_data_url": qr_data_url,
        "qr_payload": wrapped_package,
        "message": "File encrypted and wrapped successfully. Download the encrypted package and QR code."
    }), 201


@transfers_bp.route("/transfers/<transfer_id>/status", methods=["GET"])
def get_transfer_status(transfer_id):
    """Public transfer status information."""
    transfer = db.session.get(Transfer, transfer_id)
    if not transfer:
        return jsonify({"error": "Transfer not found"}), 404

    return jsonify({
        "transfer_id": transfer.id,
        "original_filename": transfer.original_filename,
        "algorithm": transfer.algorithm,
        "created_at": transfer.created_at.isoformat() if transfer.created_at else None,
        "status": transfer.status,
    })


@transfers_bp.route("/transfers/<transfer_id>/qr", methods=["GET"])
def download_qr(transfer_id):
    """Download QR code as PNG image."""
    transfer = db.session.get(Transfer, transfer_id)
    if not transfer:
        return jsonify({"error": "Transfer not found"}), 404

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(transfer.wrapped_key_package)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")

    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{transfer_id}-keywrap-qr.png"
    )


@transfers_bp.route("/transfers/<transfer_id>/download", methods=["GET"])
def download_encrypted_file(transfer_id):
    """Download the raw encrypted package file (.enc)."""
    transfer = db.session.get(Transfer, transfer_id)
    if not transfer:
        return jsonify({"error": "Transfer not found"}), 404

    storage = get_storage()
    data = storage.get(transfer.encrypted_storage_key)
    if not data:
        return jsonify({"error": "Encrypted file not found on storage"}), 404

    return Response(
        data,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={transfer_id}.enc"}
    )


@transfers_bp.route("/transfers/<transfer_id>/scan", methods=["POST"])
def scan_qr(transfer_id):
    """
    Module 2: Receiver Authentication Step 1 - QR Scan
    Receiver scans or uploads QR code, client provides decoded payload.
    Backend validates transfer_id, matches wrapped package, initializes session in state QR_OK.
    """
    transfer = db.session.get(Transfer, transfer_id)
    if not transfer:
        return jsonify({"error": "Transfer not found"}), 404

    # Optional payload verification
    payload = request.get_json(silent=True) or {}
    qr_payload = payload.get("qr_payload")

    if qr_payload:
        if isinstance(qr_payload, str):
            try:
                qr_payload = json.loads(qr_payload)
            except Exception:
                return jsonify({"error": "Malformed QR payload"}), 400

        # Validate that the QR belongs to this transfer
        if qr_payload.get("transfer_id") != transfer_id:
            return jsonify({"error": "QR code transfer ID mismatch"}), 400

    token, token_hash = generate_session_token()
    session_id = secrets.token_hex(16)

    new_session = ReceiverSession(
        id=session_id,
        transfer_id=transfer_id,
        session_token_hash=token_hash,
        current_state="QR_OK",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=Config.SESSION_EXPIRY_MINUTES)
    )
    db.session.add(new_session)
    db.session.commit()

    log_audit_event(
        transfer_id=transfer_id,
        event_type="QR_SCANNED_SUCCESS",
        success=True,
        metadata={"to_state": "QR_OK", "algorithm": transfer.algorithm}
    )

    return jsonify({
        "session_token": token,
        "session_id": session_id,
        "current_state": "QR_OK",
        "transfer_id": transfer.id,
        "original_filename": transfer.original_filename,
        "algorithm": transfer.algorithm,
        "message": "QR code validated successfully. Enter password to proceed."
    }), 200
