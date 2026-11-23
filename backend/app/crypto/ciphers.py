import base64
import hmac
import hashlib
import json
import os
from typing import Tuple, Dict, Any
from Crypto.Cipher import AES, Blowfish
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# Supported cryptographic constants
SUPPORTED_ALGORITHMS = ["AES-128-CBC", "Blowfish-CBC"]
AES_KEY_SIZE = 16       # 128 bits
AES_BLOCK_SIZE = 16     # 128 bits IV
BLOWFISH_KEY_SIZE = 16  # 128 bits
BLOWFISH_BLOCK_SIZE = 8 # 64 bits IV
HMAC_KEY_SIZE = 32      # 256 bits

class CryptoEngine:
    """Core cryptographic engine for AES-128-CBC, Blowfish-CBC, and HMAC-SHA256."""

    @staticmethod
    def generate_keys_and_iv(algorithm: str) -> Tuple[bytes, bytes, bytes]:
        """
        Generate cryptographically secure random key, IV, and independent HMAC key.
        Never reuses keys across transfers.
        """
        if algorithm == "AES-128-CBC":
            key = get_random_bytes(AES_KEY_SIZE)
            iv = get_random_bytes(AES_BLOCK_SIZE)
        elif algorithm == "Blowfish-CBC":
            key = get_random_bytes(BLOWFISH_KEY_SIZE)
            iv = get_random_bytes(BLOWFISH_BLOCK_SIZE)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Independent HMAC key for integrity verification
        hmac_key = get_random_bytes(HMAC_KEY_SIZE)
        return key, iv, hmac_key

    @staticmethod
    def compute_hmac(hmac_key: bytes, version: str, transfer_id: str, algorithm: str, iv_b64: str, ciphertext_b64: str) -> str:
        """
        Compute HMAC-SHA256 over canonical authenticated payload string:
        version:transfer_id:algorithm:iv_b64:ciphertext_b64
        """
        authenticated_data = f"{version}:{transfer_id}:{algorithm}:{iv_b64}:{ciphertext_b64}".encode("utf-8")
        h = hmac.new(hmac_key, authenticated_data, hashlib.sha256)
        return h.hexdigest()

    @staticmethod
    def verify_hmac(hmac_key: bytes, expected_hmac_hex: str, version: str, transfer_id: str, algorithm: str, iv_b64: str, ciphertext_b64: str) -> bool:
        """
        Verify HMAC using constant-time comparison to prevent timing attacks.
        """
        computed_hmac_hex = CryptoEngine.compute_hmac(hmac_key, version, transfer_id, algorithm, iv_b64, ciphertext_b64)
        return hmac.compare_digest(expected_hmac_hex, computed_hmac_hex)

    @staticmethod
    def encrypt(data_bytes: bytes, algorithm: str, key: bytes, iv: bytes) -> bytes:
        """
        Encrypt data bytes with PKCS7 padding using the selected cipher.
        """
        if algorithm == "AES-128-CBC":
            cipher = AES.new(key, AES.MODE_CBC, iv=iv)
            padded_data = pad(data_bytes, AES_BLOCK_SIZE, style="pkcs7")
            return cipher.encrypt(padded_data)
        elif algorithm == "Blowfish-CBC":
            cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv=iv)
            padded_data = pad(data_bytes, BLOWFISH_BLOCK_SIZE, style="pkcs7")
            return cipher.encrypt(padded_data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @staticmethod
    def decrypt(ciphertext: bytes, algorithm: str, key: bytes, iv: bytes) -> bytes:
        """
        Decrypt ciphertext using the cipher and unpad PKCS7.
        """
        try:
            if algorithm == "AES-128-CBC":
                cipher = AES.new(key, AES.MODE_CBC, iv=iv)
                decrypted_padded = cipher.decrypt(ciphertext)
                return unpad(decrypted_padded, AES_BLOCK_SIZE, style="pkcs7")
            elif algorithm == "Blowfish-CBC":
                cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv=iv)
                decrypted_padded = cipher.decrypt(ciphertext)
                return unpad(decrypted_padded, BLOWFISH_BLOCK_SIZE, style="pkcs7")
            else:
                raise ValueError("Invalid algorithm")
        except Exception:
            # Generic error to avoid leaking internal padding/cipher exception
            raise ValueError("Decryption failed: corrupted data or invalid key/IV")

    @classmethod
    def create_encrypted_package(cls, data_bytes: bytes, transfer_id: str, algorithm: str, key: bytes, iv: bytes, hmac_key: bytes) -> Dict[str, Any]:
        """
        Create structured encrypted package containing:
        version, transfer_id, algorithm, iv, ciphertext, hmac_tag
        Plaintext encryption key and HMAC key are NOT included in this package.
        """
        version = "1.0"
        ciphertext = cls.encrypt(data_bytes, algorithm, key, iv)
        iv_b64 = base64.b64encode(iv).decode("utf-8")
        ciphertext_b64 = base64.b64encode(ciphertext).decode("utf-8")
        hmac_tag = cls.compute_hmac(hmac_key, version, transfer_id, algorithm, iv_b64, ciphertext_b64)

        return {
            "version": version,
            "transfer_id": transfer_id,
            "algorithm": algorithm,
            "iv": iv_b64,
            "ciphertext": ciphertext_b64,
            "hmac_tag": hmac_tag,
        }
