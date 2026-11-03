import base64
import json
import os
import hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class KeyWrapper:
    """
    Secure password-based key wrapping and hashing.
    - Password hashing using salted scrypt / PBKDF2 (at least 200k iterations).
    - Key wrapping using PBKDF2-HMAC-SHA256 (200k iterations) + AES-256-GCM authenticated encryption.
    - Prevents raw key/IV exposure in QR codes.
    """

    PBKDF2_ITERATIONS = 200_000
    SALT_SIZE = 16
    NONCE_SIZE = 12

    @classmethod
    def hash_password(cls, password: str, salt: bytes = None) -> tuple[str, str]:
        """
        Hashes password using PBKDF2-HMAC-SHA256 with 200,000 iterations.
        Returns: (hash_b64, salt_b64)
        """
        if not salt:
            salt = os.urandom(cls.SALT_SIZE)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=cls.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        pwd_hash = kdf.derive(password.encode('utf-8'))
        return (
            base64.b64encode(pwd_hash).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )

    @classmethod
    def verify_password(cls, password: str, stored_hash_b64: str, stored_salt_b64: str) -> bool:
        """
        Constant-time verification of password against stored hash.
        """
        salt = base64.b64decode(stored_salt_b64.encode('utf-8'))
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=cls.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        try:
            kdf.verify(password.encode('utf-8'), base64.b64decode(stored_hash_b64.encode('utf-8')))
            return True
        except Exception:
            return False

    @classmethod
    def derive_key(cls, password: str, salt: bytes) -> bytes:
        """
        Derives a 256-bit AES-GCM wrapping key using PBKDF2-HMAC-SHA256.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=cls.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))

    @classmethod
    def wrap_keys(cls, cipher_type: str, raw_key: bytes, raw_iv: bytes, password: str, transfer_id: str) -> str:
        """
        Wraps cipher_type, raw_key, and raw_iv using AES-256-GCM authenticated encryption
        under a password-derived key.
        Returns: JSON-encoded, base64-packed QR payload string.
        """
        salt = os.urandom(cls.SALT_SIZE)
        derived_key = cls.derive_key(password, salt)

        payload_dict = {
            "cipher": cipher_type,
            "key": base64.b64encode(raw_key).decode('utf-8'),
            "iv": base64.b64encode(raw_iv).decode('utf-8'),
            "transfer_id": transfer_id
        }
        payload_bytes = json.dumps(payload_dict).encode('utf-8')

        nonce = os.urandom(cls.NONCE_SIZE)
        aesgcm = AESGCM(derived_key)
        # AESGCM encrypt appends 16-byte tag to ciphertext
        ciphertext_and_tag = aesgcm.encrypt(nonce, payload_bytes, transfer_id.encode('utf-8'))

        qr_envelope = {
            "v": 2,
            "tid": transfer_id,
            "salt": base64.b64encode(salt).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "blob": base64.b64encode(ciphertext_and_tag).decode('utf-8')
        }

        # Encode envelope as base64 string for QR payload
        return base64.urlsafe_b64encode(json.dumps(qr_envelope).encode('utf-8')).decode('utf-8')

    @classmethod
    def unwrap_keys(cls, qr_payload_str: str, password: str) -> dict:
        """
        Unwraps and decrypts the QR payload using the password.
        Returns: dict with {"cipher": str, "raw_key": bytes, "raw_iv": bytes, "transfer_id": str}
        Raises: ValueError on invalid envelope or wrong password (InvalidTag).
        """
        try:
            # Handle potential urlsafe padding
            rem = len(qr_payload_str) % 4
            if rem > 0:
                qr_payload_str += "=" * (4 - rem)
            envelope_bytes = base64.urlsafe_b64decode(qr_payload_str.encode('utf-8'))
            envelope = json.loads(envelope_bytes.decode('utf-8'))

            transfer_id = envelope["tid"]
            salt = base64.b64decode(envelope["salt"].encode('utf-8'))
            nonce = base64.b64decode(envelope["nonce"].encode('utf-8'))
            ciphertext_and_tag = base64.b64decode(envelope["blob"].encode('utf-8'))
        except Exception as e:
            raise ValueError(f"Malformed QR envelope: {e}") from e

        derived_key = cls.derive_key(password, salt)
        aesgcm = AESGCM(derived_key)

        try:
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, transfer_id.encode('utf-8'))
        except Exception as e:
            raise ValueError("Failed to unwrap keys: Incorrect password or tampered QR payload") from e

        try:
            payload = json.loads(decrypted_bytes.decode('utf-8'))
            return {
                "cipher": payload["cipher"],
                "raw_key": base64.b64decode(payload["key"].encode('utf-8')),
                "raw_iv": base64.b64decode(payload["iv"].encode('utf-8')),
                "transfer_id": payload["transfer_id"]
            }
        except Exception as e:
            raise ValueError(f"Corrupted unwrapped key payload: {e}") from e

