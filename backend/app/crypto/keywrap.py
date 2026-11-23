import json
import os
from typing import Dict, Any
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

PBKDF2_ITERATIONS = 200_000
SALT_SIZE = 16
GCM_NONCE_SIZE = 12
WRAPPING_KEY_SIZE = 32  # 256 bits

class KeyWrapManager:
    """Password-based key wrapping using PBKDF2-HMAC-SHA256 and AES-256-GCM."""

    @staticmethod
    def derive_wrapping_key(password: str, salt: bytes) -> bytes:
        """Derive 256-bit wrapping key with 200,000 PBKDF2-HMAC-SHA256 iterations."""
        return PBKDF2(
            password=password.encode("utf-8"),
            salt=salt,
            dkLen=WRAPPING_KEY_SIZE,
            count=PBKDF2_ITERATIONS,
            hmac_hash_module=SHA256
        )

    @classmethod
    def wrap_keys(cls, password: str, transfer_id: str, algorithm: str,
                  encryption_key: bytes, iv: bytes, hmac_key: bytes, salt: bytes = None) -> Dict[str, Any]:
        """
        Wrap encryption key, IV, HMAC key, and algorithm metadata using AES-256-GCM.
        Authenticated associated data (AAD) binds the payload to transfer_id.
        """
        if salt is None:
            salt = get_random_bytes(SALT_SIZE)

        wrapping_key = cls.derive_wrapping_key(password, salt)
        nonce = get_random_bytes(GCM_NONCE_SIZE)

        cipher = AES.new(wrapping_key, AES.MODE_GCM, nonce=nonce)
        cipher.update(transfer_id.encode("utf-8"))  # AAD binding

        secrets_payload = json.dumps({
            "encryption_key": encryption_key.hex(),
            "iv": iv.hex(),
            "hmac_key": hmac_key.hex(),
            "algorithm": algorithm,
        }).encode("utf-8")

        ciphertext, tag = cipher.encrypt_and_digest(secrets_payload)

        return {
            "version": "1.0",
            "transfer_id": transfer_id,
            "algorithm": algorithm,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "tag": tag.hex(),
        }

    @classmethod
    def unwrap_keys(cls, password: str, wrapped_package: Dict[str, Any]) -> Dict[str, bytes]:
        """
        Unwrap and authenticate the protected key package using AES-256-GCM.
        Returns bytes dict: { 'encryption_key', 'iv', 'hmac_key', 'algorithm' }.
        Raises ValueError if password is wrong or package is corrupted/tampered.
        """
        try:
            salt = bytes.fromhex(wrapped_package["salt"])
            nonce = bytes.fromhex(wrapped_package["nonce"])
            ciphertext = bytes.fromhex(wrapped_package["ciphertext"])
            tag = bytes.fromhex(wrapped_package["tag"])
            transfer_id = wrapped_package["transfer_id"]

            wrapping_key = cls.derive_wrapping_key(password, salt)

            cipher = AES.new(wrapping_key, AES.MODE_GCM, nonce=nonce)
            cipher.update(transfer_id.encode("utf-8"))  # Verify AAD

            decrypted_json_bytes = cipher.decrypt_and_verify(ciphertext, tag)
            secrets = json.loads(decrypted_json_bytes.decode("utf-8"))

            return {
                "encryption_key": bytes.fromhex(secrets["encryption_key"]),
                "iv": bytes.fromhex(secrets["iv"]),
                "hmac_key": bytes.fromhex(secrets["hmac_key"]),
                "algorithm": secrets["algorithm"],
            }
        except Exception:
            # Strictly generic error without leaking whether tag, salt, or JSON failed
            raise ValueError("Authentication failed: invalid password or corrupted package")
