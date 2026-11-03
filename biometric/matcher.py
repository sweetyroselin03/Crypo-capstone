import time
import numpy as np
from database import SessionLocal, Transfer, BiometricTemplate, log_audit
from biometric.features import BiometricFeatureExtractor


class BiometricMatcher:
    """
    Biometric enrollment aggregator, matcher, and rate-limited verification engine.
    - Enrollment: Aggregates 15-20 quality frames into an enrolled centroid template.
    - Verification: Compares live query embedding against encrypted stored template using cosine distance.
    - Enforces max 3 attempts before a 15-minute lockout.
    """

    DEFAULT_SIMILARITY_THRESHOLD = 0.90  # Cosine similarity >= 0.90 => MATCH
    MAX_FAILED_ATTEMPTS = 3
    LOCKOUT_DURATION_SECONDS = 900.0     # 15 minutes

    @classmethod
    def aggregate_enrollment(cls, embeddings_list: list[np.ndarray]) -> np.ndarray:
        """
        Combines 15-20 frame embeddings into a single robust template via centroid averaging.
        """
        if not embeddings_list:
            raise ValueError("No embeddings provided for enrollment")

        matrix = np.array(embeddings_list, dtype=np.float32)
        # Centroid mean
        mean_embedding = np.mean(matrix, axis=0)

        # Re-normalize to unit length
        norm = np.linalg.norm(mean_embedding)
        if norm > 1e-6:
            mean_embedding = mean_embedding / norm

        return mean_embedding

    @classmethod
    def save_enrolled_template(cls, transfer_id: str, final_embedding: np.ndarray, sample_count: int):
        """
        Encrypts template at rest (AES-GCM) and saves to database.
        """
        enc_blob, nonce = BiometricFeatureExtractor.encrypt_template(final_embedding)
        db = SessionLocal()
        try:
            # Remove any prior template for re-enrollment support
            db.query(BiometricTemplate).filter(BiometricTemplate.transfer_id == transfer_id).delete()

            tmpl = BiometricTemplate(
                transfer_id=transfer_id,
                encrypted_template=enc_blob,
                nonce=nonce,
                sample_count=sample_count
            )
            db.add(tmpl)
            db.commit()
            log_audit(
                step="EYE_ENROLL",
                status="SUCCESS",
                details=f"Stored encrypted biometric template from {sample_count} frames",
                transfer_id=transfer_id
            )
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @classmethod
    def verify_live_scan(cls, transfer_id: str, query_embedding: np.ndarray, threshold: float = None) -> dict:
        """
        Verifies live scan against stored encrypted biometric template.
        Enforces 3-attempt limit with 15-minute lockout.
        Returns: {
            "match": bool,
            "similarity": float,
            "distance": float,
            "threshold": float,
            "attempts_left": int,
            "locked": bool,
            "message": str
        }
        """
        if threshold is None:
            threshold = cls.DEFAULT_SIMILARITY_THRESHOLD

        db = SessionLocal()
        try:
            transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
            if not transfer:
                return {"match": False, "message": "Transfer not found", "locked": False}

            now = time.time()
            if transfer.eye_locked_until and transfer.eye_locked_until > now:
                mins_left = int((transfer.eye_locked_until - now) / 60) + 1
                return {
                    "match": False,
                    "similarity": 0.0,
                    "distance": 1.0,
                    "threshold": threshold,
                    "attempts_left": 0,
                    "locked": True,
                    "message": f"Biometric verification is locked. Please wait {mins_left} minutes."
                }

            template_record = db.query(BiometricTemplate).filter(BiometricTemplate.transfer_id == transfer_id).first()
            if not template_record:
                return {"match": False, "message": "No enrolled biometric template found for this transfer.", "locked": False}

            # Decrypt stored template at rest
            stored_embedding = BiometricFeatureExtractor.decrypt_template(
                template_record.encrypted_template,
                template_record.nonce
            )

            # Compute Cosine Similarity = dot product of unit vectors
            sim = float(np.dot(query_embedding, stored_embedding))
            # Clamp between -1.0 and 1.0
            sim = max(-1.0, min(1.0, sim))
            dist = float(1.0 - sim)

            is_match = (sim >= threshold)

            if is_match:
                # Reset failed attempts
                transfer.failed_eye_attempts = 0
                transfer.eye_locked_until = 0.0
                db.commit()

                log_audit(
                    step="EYE_VERIFY",
                    status="SUCCESS",
                    details=f"Biometric eye scan matched (similarity: {sim:.3f} >= {threshold:.3f})",
                    transfer_id=transfer_id
                )
                return {
                    "match": True,
                    "similarity": round(sim, 4),
                    "distance": round(dist, 4),
                    "threshold": threshold,
                    "attempts_left": cls.MAX_FAILED_ATTEMPTS,
                    "locked": False,
                    "message": "Biometric match verified successfully! Access granted."
                }
            else:
                transfer.failed_eye_attempts = (transfer.failed_eye_attempts or 0) + 1
                attempts_left = max(0, cls.MAX_FAILED_ATTEMPTS - transfer.failed_eye_attempts)
                locked = False

                if transfer.failed_eye_attempts >= cls.MAX_FAILED_ATTEMPTS:
                    transfer.eye_locked_until = now + cls.LOCKOUT_DURATION_SECONDS
                    locked = True
                    log_audit(
                        step="EYE_VERIFY",
                        status="LOCKED",
                        details=f"Transfer locked for 15 minutes after {cls.MAX_FAILED_ATTEMPTS} failed eye verification attempts",
                        transfer_id=transfer_id
                    )
                else:
                    log_audit(
                        step="EYE_VERIFY",
                        status="FAILURE",
                        details=f"Biometric eye mismatch (similarity: {sim:.3f} < {threshold:.3f}, attempts left: {attempts_left})",
                        transfer_id=transfer_id
                    )

                db.commit()

                msg = "Biometric mismatch: Eye scan does not match enrolled template."
                if locked:
                    msg = f"Biometric mismatch: Maximum attempts exceeded. Transfer locked for 15 minutes."
                else:
                    msg += f" {attempts_left} attempt(s) remaining."

                return {
                    "match": False,
                    "similarity": round(sim, 4),
                    "distance": round(dist, 4),
                    "threshold": threshold,
                    "attempts_left": attempts_left,
                    "locked": locked,
                    "message": msg
                }
        finally:
            db.close()
