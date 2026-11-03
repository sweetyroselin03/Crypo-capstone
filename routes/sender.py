import os
import uuid
import io
import pandas as pd
import qrcode
from flask import Blueprint, request, render_template, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from database import SessionLocal, Transfer, log_audit
from crypto.aes import AESCipher
from crypto.blowfish import BlowfishCipher
from crypto.keywrap import KeyWrapper

sender_bp = Blueprint('sender', __name__)

ALLOWED_EXTENSIONS = {'xlsx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@sender_bp.route('/sender', methods=['GET'])
def sender_page():
    return render_template('sender.html')


@sender_bp.route('/sender/upload', methods=['POST'])
def upload_and_encrypt():
    """
    Handles file upload, conversion to CSV bytes, encryption (AES or Blowfish),
    password hashing, key wrapping, and QR generation.
    """
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files['file']
    cipher_type = request.form.get('cipher_type', 'AES').upper()
    password = request.form.get('password', '').strip()

    if file.filename == '':
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file format. Only Excel (.xlsx) files are supported."}), 400

    if not password or len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters long."}), 400

    if cipher_type not in ['AES', 'BLOWFISH']:
        return jsonify({"success": False, "error": "Unsupported cipher. Choose AES or Blowfish."}), 400

    try:
        # Read Excel file and convert to CSV bytes
        file_bytes = file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            return jsonify({"success": False, "error": "File size exceeds 10 MB limit."}), 400

        excel_io = io.BytesIO(file_bytes)
        df = pd.read_excel(excel_io)
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        file_size_bytes = len(csv_bytes)

        transfer_id = f"tr-{uuid.uuid4().hex[:12]}"

        # Encrypt based on selection
        if cipher_type == 'AES':
            encrypted_blob, raw_key, raw_iv, enc_time_ms = AESCipher.encrypt(csv_bytes)
        else:
            encrypted_blob, raw_key, raw_iv, enc_time_ms = BlowfishCipher.encrypt(csv_bytes)

        # Performance metric: Throughput = KB / s
        size_kb = file_size_bytes / 1024.0
        time_seconds = max(enc_time_ms / 1000.0, 1e-6)
        throughput_kb_s = size_kb / time_seconds

        # Secure password hashing (salted PBKDF2 200k iterations)
        pwd_hash, pwd_salt = KeyWrapper.hash_password(password)

        # Secure key wrapping for QR (AES-256-GCM under password-derived key)
        qr_payload = KeyWrapper.wrap_keys(
            cipher_type=cipher_type,
            raw_key=raw_key,
            raw_iv=raw_iv,
            password=password,
            transfer_id=transfer_id
        )

        # Save encrypted file
        enc_dir = os.path.abspath(os.path.join(current_app.root_path, 'data', 'encrypted'))
        os.makedirs(enc_dir, exist_ok=True)
        enc_file_path = os.path.join(enc_dir, f"{transfer_id}.enc")
        with open(enc_file_path, 'wb') as f:
            f.write(encrypted_blob)

        # Generate QR code image
        qr_dir = os.path.abspath(os.path.join(current_app.root_path, 'data', 'qrcodes'))
        os.makedirs(qr_dir, exist_ok=True)
        qr_image_path = os.path.join(qr_dir, f"{transfer_id}.png")

        qr_img = qrcode.make(qr_payload)
        qr_img.save(qr_image_path)

        # Save to database
        db = SessionLocal()
        try:
            transfer = Transfer(
                id=transfer_id,
                original_filename=secure_filename(file.filename),
                file_size_bytes=file_size_bytes,
                cipher_type=cipher_type,
                encrypted_file_path=enc_file_path,
                password_hash=pwd_hash,
                password_salt=pwd_salt,
                qr_payload=qr_payload,
                qr_image_path=qr_image_path,
                enc_time_ms=enc_time_ms,
                throughput_kb_s=throughput_kb_s
            )
            db.add(transfer)
            db.commit()

            log_audit(
                step="FILE_ENCRYPT",
                status="SUCCESS",
                details=f"File {file.filename} encrypted using {cipher_type} (Size: {size_kb:.2f} KB, Time: {enc_time_ms:.2f} ms)",
                transfer_id=transfer_id,
                ip_address=request.remote_addr or "127.0.0.1"
            )
        finally:
            db.close()

        return jsonify({
            "success": True,
            "transfer_id": transfer_id,
            "filename": file.filename,
            "cipher": cipher_type,
            "size_kb": round(size_kb, 2),
            "enc_time_ms": round(enc_time_ms, 2),
            "throughput_kb_s": round(throughput_kb_s, 2),
            "qr_image_url": f"/download/qr/{transfer_id}",
            "encrypted_file_url": f"/download/encrypted/{transfer_id}",
            "qr_payload": qr_payload
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Encryption failed: {str(e)}"}), 500


@sender_bp.route('/download/encrypted/<transfer_id>', methods=['GET'])
def download_encrypted(transfer_id):
    db = SessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer or not os.path.exists(transfer.encrypted_file_path):
            return "Encrypted file not found", 404
        return send_file(
            transfer.encrypted_file_path,
            as_attachment=True,
            download_name=f"{transfer.original_filename}.enc",
            mimetype="application/octet-stream"
        )
    finally:
        db.close()


@sender_bp.route('/download/qr/<transfer_id>', methods=['GET'])
def download_qr(transfer_id):
    db = SessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer or not os.path.exists(transfer.qr_image_path):
            return "QR Code image not found", 404
        return send_file(
            transfer.qr_image_path,
            as_attachment=False,
            mimetype="image/png"
        )
    finally:
        db.close()

