import os
import io
import time
import base64
import cv2
import numpy as np
import pandas as pd
from flask import Blueprint, request, render_template, jsonify, session, send_file, current_app
from database import SessionLocal, Transfer, BiometricTemplate, log_audit
from state_machine import ReceiverStateMachine, ReceiverState, StateMachineError
from crypto.aes import AESCipher
from crypto.blowfish import BlowfishCipher
from crypto.keywrap import KeyWrapper
from biometric.detect import EyeDetector, QualityError
from biometric.liveness import LivenessTracker
from biometric.features import BiometricFeatureExtractor
from biometric.matcher import BiometricMatcher

receiver_bp = Blueprint('receiver', __name__)

eye_detector = EyeDetector()
liveness_trackers: dict[str, LivenessTracker] = {}
enrollment_buffers: dict[str, list[np.ndarray]] = {}


def get_liveness_tracker(session_id: str) -> LivenessTracker:
    if session_id not in liveness_trackers:
        liveness_trackers[session_id] = LivenessTracker()
    return liveness_trackers[session_id]


def decode_base64_image(b64_string: str) -> np.ndarray:
    if ',' in b64_string:
        b64_string = b64_string.split(',')[1]
    img_bytes = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img_bgr


@receiver_bp.route('/receiver', methods=['GET'])
def receiver_page():
    ReceiverStateMachine.reset()
    return render_template('receiver.html')


@receiver_bp.route('/api/receiver/state', methods=['GET'])
def get_state():
    return jsonify({
        "current_state": ReceiverStateMachine.get_current_state().value,
        "transfer_id": ReceiverStateMachine.get_current_transfer_id()
    })


# ==========================================
# STEP 1: QR Scan (Camera or Upload)
# ==========================================
@receiver_bp.route('/api/receiver/qr-scan', methods=['POST'])
def qr_scan():
    """
    Step 1: Scans and decodes QR payload.
    Validates transfer existence and transitions to QR_OK.
    """
    data = request.get_json(silent=True) or {}
    qr_payload_text = data.get('qr_payload', '').strip()

    # Support QR image upload as multipart or base64
    if not qr_payload_text and 'qr_image' in request.files:
        file = request.files['qr_image']
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            detector = cv2.QRCodeDetector()
            decoded_text, _, _ = detector.detectAndDecode(img)
            if decoded_text:
                qr_payload_text = decoded_text

    if not qr_payload_text and data.get('qr_image_b64'):
        img = decode_base64_image(data.get('qr_image_b64'))
        if img is not None:
            detector = cv2.QRCodeDetector()
            decoded_text, _, _ = detector.detectAndDecode(img)
            if decoded_text:
                qr_payload_text = decoded_text

    if not qr_payload_text:
        return jsonify({"success": False, "error": "No QR payload detected or provided."}), 400

    # Parse envelope metadata (transfer_id)
    try:
        rem = len(qr_payload_text) % 4
        padded_b64 = qr_payload_text + ("=" * (4 - rem) if rem else "")
        raw_json = base64.urlsafe_b64decode(padded_b64.encode('utf-8')).decode('utf-8')
        import json
        envelope = json.loads(raw_json)
        transfer_id = envelope.get("tid")
    except Exception as e:
        return jsonify({"success": False, "error": f"Invalid QR code envelope format: {str(e)}"}), 400

    db = SessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer:
            return jsonify({"success": False, "error": "Transfer record not found for this QR code."}), 404

        # Check for active lockout
        now = time.time()
        if transfer.password_locked_until and transfer.password_locked_until > now:
            mins = int((transfer.password_locked_until - now) / 60) + 1
            return jsonify({"success": False, "error": f"Transfer is locked. Try again in {mins} minutes."}), 423

        if transfer.eye_locked_until and transfer.eye_locked_until > now:
            mins = int((transfer.eye_locked_until - now) / 60) + 1
            return jsonify({"success": False, "error": f"Biometric verification locked. Try again in {mins} minutes."}), 423

        # Transition state
        session['qr_payload'] = qr_payload_text
        enrollment_buffers[transfer_id] = []
        ReceiverStateMachine.transition_to(ReceiverState.QR_OK, transfer_id)

        log_audit(
            step="QR_SCAN",
            status="SUCCESS",
            details=f"QR code scanned successfully for transfer {transfer_id}",
            transfer_id=transfer_id,
            ip_address=request.remote_addr or "127.0.0.1"
        )

        return jsonify({
            "success": True,
            "transfer_id": transfer_id,
            "filename": transfer.original_filename,
            "cipher": transfer.cipher_type,
            "next_step": ReceiverState.PASSWORD_OK.value
        })
    finally:
        db.close()


# ==========================================
# STEP 2: Password Verification & Key Unwrap
# ==========================================
@receiver_bp.route('/api/receiver/verify-password', methods=['POST'])
def verify_password():
    """
    Step 2: Requires QR_OK state.
    Verifies transfer password and securely unwraps AES/Blowfish keys.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.PASSWORD_OK)
    except StateMachineError as sme:
        return jsonify({"success": False, "error": sme.message}), sme.status_code

    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    data = request.get_json() or {}
    password = data.get('password', '').strip()

    if not password:
        return jsonify({"success": False, "error": "Password cannot be empty"}), 400

    db = SessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer:
            return jsonify({"success": False, "error": "Transfer not found"}), 404

        # Rate-limiting password check (5 attempts -> 15 min lock)
        now = time.time()
        if transfer.password_locked_until and transfer.password_locked_until > now:
            mins = int((transfer.password_locked_until - now) / 60) + 1
            return jsonify({"success": False, "error": f"Password attempts exceeded. Locked for {mins} min."}), 423

        qr_payload = session.get('qr_payload') or transfer.qr_payload
        try:
            unwrapped = KeyWrapper.unwrap_keys(qr_payload, password)
        except ValueError:
            transfer.failed_password_attempts = (transfer.failed_password_attempts or 0) + 1
            remaining = max(0, 5 - transfer.failed_password_attempts)
            if transfer.failed_password_attempts >= 5:
                transfer.password_locked_until = now + 900.0  # 15 minutes
                db.commit()
                log_audit(
                    step="PASSWORD",
                    status="LOCKED",
                    details=f"Transfer {transfer_id} locked after 5 failed password attempts",
                    transfer_id=transfer_id,
                    ip_address=request.remote_addr or "127.0.0.1"
                )
                return jsonify({"success": False, "error": "5 failed attempts. Transfer locked for 15 minutes."}), 423

            db.commit()
            log_audit(
                step="PASSWORD",
                status="FAILURE",
                details=f"Incorrect password attempt for {transfer_id} ({remaining} remaining)",
                transfer_id=transfer_id,
                ip_address=request.remote_addr or "127.0.0.1"
            )
            return jsonify({"success": False, "error": f"Incorrect password. {remaining} attempt(s) remaining."}), 401

        # Correct password! Reset failed counter
        transfer.failed_password_attempts = 0
        db.commit()

        # Cache unwrapped keys in server-side session
        session['unwrapped_key'] = base64.b64encode(unwrapped["raw_key"]).decode('utf-8')
        session['unwrapped_iv'] = base64.b64encode(unwrapped["raw_iv"]).decode('utf-8')
        session['unwrapped_cipher'] = unwrapped["cipher"]

        ReceiverStateMachine.transition_to(ReceiverState.PASSWORD_OK, transfer_id)

        log_audit(
            step="PASSWORD",
            status="SUCCESS",
            details=f"Password verified and keys unwrapped for {transfer_id}",
            transfer_id=transfer_id,
            ip_address=request.remote_addr or "127.0.0.1"
        )

        return jsonify({
            "success": True,
            "message": "Password verified! Key successfully unwrapped.",
            "next_step": ReceiverState.KEY_SHOWN.value
        })
    finally:
        db.close()


# ==========================================
# STEP 3: Secret Key Reveal (Auto-hides in 30s)
# ==========================================
@receiver_bp.route('/api/receiver/secret-key', methods=['GET'])
def get_secret_key():
    """
    Step 3: Requires PASSWORD_OK state.
    Returns key + IV. Never logged to disk or audit logs!
    Transitions to KEY_SHOWN.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.KEY_SHOWN)
    except StateMachineError as sme:
        return jsonify({"success": False, "error": sme.message}), sme.status_code

    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    key_b64 = session.get('unwrapped_key')
    iv_b64 = session.get('unwrapped_iv')
    cipher = session.get('unwrapped_cipher', 'AES')

    if not key_b64 or not iv_b64:
        return jsonify({"success": False, "error": "Unwrapped key session expired. Re-authenticate."}), 403

    ReceiverStateMachine.transition_to(ReceiverState.KEY_SHOWN, transfer_id)

    raw_key = base64.b64decode(key_b64.encode('utf-8'))
    raw_iv = base64.b64decode(iv_b64.encode('utf-8'))

    # Crucial security: Audit log records ONLY the event, NEVER raw key or IV bytes
    log_audit(
        step="KEY_REVEAL",
        status="SUCCESS",
        details="Secret key revealed on screen (auto-masked, 30s timer)",
        transfer_id=transfer_id,
        ip_address=request.remote_addr or "127.0.0.1"
    )

    return jsonify({
        "success": True,
        "cipher": cipher,
        "key_hex": raw_key.hex(),
        "iv_hex": raw_iv.hex(),
        "key_base64": key_b64,
        "iv_base64": iv_b64,
        "auto_hide_seconds": 30,
        "next_step": ReceiverState.EYE_ENROLLED.value
    })


# ==========================================
# STEP 4: Eye Scan Enrollment ("Train Mode")
# ==========================================
@receiver_bp.route('/api/receiver/eye-train-frame', methods=['POST'])
def eye_train_frame():
    """
    Step 4: Trains biometric template over 15-20 frames.
    Quality check validates sharpness and lighting.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.EYE_ENROLLED)
    except StateMachineError as sme:
        return jsonify({"success": False, "error": sme.message}), sme.status_code

    data = request.get_json() or {}
    frame_b64 = data.get('frame')
    if not frame_b64:
        return jsonify({"success": False, "error": "No camera frame provided"}), 400

    try:
        img_bgr = decode_base64_image(frame_b64)
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to decode camera frame"}), 400

    try:
        detection = eye_detector.detect_and_crop_eyes(img_bgr)
    except QualityError as qe:
        return jsonify({
            "success": False,
            "quality_error": True,
            "message": str(qe)
        }), 422
    except Exception as e:
        return jsonify({"success": False, "error": f"Detection error: {str(e)}"}), 500

    embedding = BiometricFeatureExtractor.extract_embedding(detection["left_eye"], detection["right_eye"])

    # Store frame embedding in server-side memory buffer (never in client cookie)
    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    if transfer_id not in enrollment_buffers:
        enrollment_buffers[transfer_id] = []
    enrollment_buffers[transfer_id].append(embedding)

    count = len(enrollment_buffers[transfer_id])
    target = 20

    return jsonify({
        "success": True,
        "captured": count,
        "target": target,
        "ear": round(detection["ear"], 3),
        "message": f"Frame {count}/{target} captured with good quality!"
    })


@receiver_bp.route('/api/receiver/eye-enroll-complete', methods=['POST'])
def eye_enroll_complete():
    """
    Finalizes Step 4 enrollment by computing centroid template,
    encrypting it at rest (AES-GCM), and saving to database.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.EYE_ENROLLED)
    except StateMachineError as sme:
        return jsonify({"success": False, "error": sme.message}), sme.status_code

    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    embeddings = enrollment_buffers.get(transfer_id, [])

    if len(embeddings) < 15:
        return jsonify({
            "success": False,
            "error": f"Insufficient frames for enrollment ({len(embeddings)}/15 required). Please continue scanning."
        }), 400

    final_centroid = BiometricMatcher.aggregate_enrollment(embeddings)
    BiometricMatcher.save_enrolled_template(transfer_id, final_centroid, sample_count=len(embeddings))

    # Clear memory buffer after successful template enrollment
    enrollment_buffers.pop(transfer_id, None)

    ReceiverStateMachine.transition_to(ReceiverState.EYE_ENROLLED, transfer_id)

    # Initialize liveness tracker for Step 5
    tracker = get_liveness_tracker(session.sid if hasattr(session, 'sid') else transfer_id)
    tracker.reset(challenge_type="BLINK")

    return jsonify({
        "success": True,
        "samples_enrolled": len(embeddings),
        "message": "Biometric template enrolled and encrypted at rest!",
        "next_step": ReceiverState.EYE_VERIFIED.value
    })


@receiver_bp.route('/api/receiver/eye-re-enroll', methods=['POST'])
def eye_re_enroll():
    """
    Allows user to re-enroll eye biometric template if desired.
    """
    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    if transfer_id:
        enrollment_buffers[transfer_id] = []
    return jsonify({"success": True, "message": "Biometric buffer cleared. Ready for re-enrollment."})


# ==========================================
# STEP 5: Eye Scan Verification & Liveness
# ==========================================
@receiver_bp.route('/api/receiver/eye-verify-frame', methods=['POST'])
def eye_verify_frame():
    """
    Step 5: Requires EYE_ENROLLED.
    Validates anti-spoofing liveness challenge (natural blink) and matches
    live scan against stored encrypted biometric template.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.EYE_VERIFIED)
    except StateMachineError as sme:
        return jsonify({"success": False, "error": sme.message}), sme.status_code

    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    data = request.get_json() or {}
    frame_b64 = data.get('frame')

    if not frame_b64:
        return jsonify({"success": False, "error": "No camera frame provided"}), 400

    img_bgr = decode_base64_image(frame_b64)

    try:
        detection = eye_detector.detect_and_crop_eyes(img_bgr)
    except QualityError as qe:
        return jsonify({
            "success": False,
            "quality_error": True,
            "message": str(qe)
        }), 422
    except Exception as e:
        return jsonify({"success": False, "error": f"Eye detection error: {str(e)}"}), 500

    # Liveness check
    session_key = session.sid if hasattr(session, 'sid') else transfer_id
    tracker = get_liveness_tracker(session_key)
    liveness_status = tracker.update(detection["ear"], detection["left_eye"])

    # If liveness challenge is not yet passed, prompt user to blink
    if not liveness_status["liveness_passed"]:
        return jsonify({
            "success": False,
            "liveness_pending": True,
            "ear": round(detection["ear"], 3),
            "state": liveness_status["state"],
            "prompt": liveness_status["prompt"],
            "message": liveness_status["prompt"]
        })

    # Liveness passed! Perform biometric matching
    query_emb = BiometricFeatureExtractor.extract_embedding(detection["left_eye"], detection["right_eye"])
    match_result = BiometricMatcher.verify_live_scan(transfer_id, query_emb)

    if match_result["match"]:
        ReceiverStateMachine.transition_to(ReceiverState.EYE_VERIFIED, transfer_id)
        return jsonify({
            "success": True,
            "match": True,
            "similarity": match_result["similarity"],
            "distance": match_result["distance"],
            "threshold": match_result["threshold"],
            "message": match_result["message"],
            "next_step": ReceiverState.DATA_VIEW.value
        })
    else:
        return jsonify({
            "success": False,
            "match": False,
            "locked": match_result.get("locked", False),
            "similarity": match_result.get("similarity", 0.0),
            "distance": match_result.get("distance", 1.0),
            "threshold": match_result.get("threshold", 0.90),
            "attempts_left": match_result.get("attempts_left", 0),
            "message": match_result["message"]
        }), (423 if match_result.get("locked") else 401)


# ==========================================
# STEP 6: View Data & Excel Download
# ==========================================
@receiver_bp.route('/api/receiver/view-data', methods=['GET'])
def view_data():
    """
    Step 6: Requires EYE_VERIFIED state.
    Decrypts encrypted file in memory and returns tabular data for browser rendering.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.DATA_VIEW)
    except StateMachineError as sme:
        return jsonify({"success": False, "error": sme.message}), sme.status_code

    transfer_id = ReceiverStateMachine.get_current_transfer_id()
    key_b64 = session.get('unwrapped_key')
    iv_b64 = session.get('unwrapped_iv')
    cipher = session.get('unwrapped_cipher', 'AES')

    if not key_b64 or not iv_b64:
        return jsonify({"success": False, "error": "Session key unavailable"}), 403

    db = SessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer or not os.path.exists(transfer.encrypted_file_path):
            return jsonify({"success": False, "error": "Encrypted file not found on server"}), 404

        with open(transfer.encrypted_file_path, 'rb') as f:
            encrypted_blob = f.read()

        raw_key = base64.b64decode(key_b64.encode('utf-8'))
        raw_iv = base64.b64decode(iv_b64.encode('utf-8'))

        # Decrypt in memory
        if cipher == 'AES':
            decrypted_csv_bytes, dec_time = AESCipher.decrypt(encrypted_blob, raw_key, raw_iv)
        else:
            decrypted_csv_bytes, dec_time = BlowfishCipher.decrypt(encrypted_blob, raw_key, raw_iv)

        # Parse CSV with pandas
        csv_stream = io.StringIO(decrypted_csv_bytes.decode('utf-8', errors='replace'))
        df = pd.read_csv(csv_stream)

        # Transition state
        ReceiverStateMachine.transition_to(ReceiverState.DATA_VIEW, transfer_id)

        log_audit(
            step="DATA_VIEW",
            status="SUCCESS",
            details=f"Decrypted and displayed {len(df)} records from {transfer.original_filename} in browser",
            transfer_id=transfer_id,
            ip_address=request.remote_addr or "127.0.0.1"
        )

        return jsonify({
            "success": True,
            "filename": transfer.original_filename,
            "cipher": cipher,
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
            "total_rows": len(df),
            "dec_time_ms": round(dec_time, 2),
            "download_excel_url": f"/download/decrypted-excel/{transfer_id}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Decryption failed: {str(e)}"}), 500
    finally:
        db.close()


@receiver_bp.route('/download/decrypted-excel/<transfer_id>', methods=['GET'])
def download_decrypted_excel(transfer_id):
    """
    Step 6 Download: Decrypts file in-memory and streams valid .xlsx Excel workbook.
    """
    try:
        ReceiverStateMachine.require_step(ReceiverState.DATA_VIEW, transfer_id)
    except StateMachineError as sme:
        return sme.message, sme.status_code

    key_b64 = session.get('unwrapped_key')
    iv_b64 = session.get('unwrapped_iv')
    cipher = session.get('unwrapped_cipher', 'AES')

    if not key_b64 or not iv_b64:
        return "Session expired", 403

    db = SessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        if not transfer or not os.path.exists(transfer.encrypted_file_path):
            return "File not found", 404

        with open(transfer.encrypted_file_path, 'rb') as f:
            encrypted_blob = f.read()

        raw_key = base64.b64decode(key_b64.encode('utf-8'))
        raw_iv = base64.b64decode(iv_b64.encode('utf-8'))

        if cipher == 'AES':
            decrypted_csv_bytes, _ = AESCipher.decrypt(encrypted_blob, raw_key, raw_iv)
        else:
            decrypted_csv_bytes, _ = BlowfishCipher.decrypt(encrypted_blob, raw_key, raw_iv)

        csv_stream = io.StringIO(decrypted_csv_bytes.decode('utf-8', errors='replace'))
        df = pd.read_csv(csv_stream)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        log_audit(
            step="DATA_DOWNLOAD",
            status="SUCCESS",
            details=f"Downloaded decrypted Excel spreadsheet: {transfer.original_filename}",
            transfer_id=transfer_id,
            ip_address=request.remote_addr or "127.0.0.1"
        )

        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=f"decrypted_{transfer.original_filename}",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    finally:
        db.close()
