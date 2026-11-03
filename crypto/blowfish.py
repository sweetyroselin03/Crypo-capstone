import os
import time
from Crypto.Cipher import Blowfish
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend


class BlowfishCipher:
    """
    Blowfish-CBC encryption and decryption with PKCS7 padding (8-byte block size)
    and HMAC-SHA256 integrity protection.
    """

    KEY_SIZE = 8   # 64-bit key (as specified in capstone requirements)
    IV_SIZE = 8    # 64-bit IV (Blowfish block size is 8 bytes)
    TAG_SIZE = 32  # SHA-256 HMAC (256-bit)
    BLOCK_SIZE = 8

    @classmethod
    def generate_key(cls) -> bytes:
        return os.urandom(cls.KEY_SIZE)

    @classmethod
    def generate_iv(cls) -> bytes:
        return os.urandom(cls.IV_SIZE)

    @classmethod
    def encrypt(cls, plaintext: bytes, key: bytes = None, iv: bytes = None) -> tuple[bytes, bytes, bytes, float]:
        """
        Encrypts plaintext with Blowfish-CBC and computes HMAC-SHA256 over IV + ciphertext.
        Returns: (encrypted_blob, key, iv, elapsed_ms)
        Format of encrypted_blob: IV (8B) + HMAC_TAG (32B) + CIPHERTEXT
        """
        if not key:
            key = cls.generate_key()
        if len(key) not in range(4, 57):
            raise ValueError(f"Blowfish key must be between 4 and 56 bytes (got {len(key)})")
        if not iv:
            iv = cls.generate_iv()
        if len(iv) != cls.IV_SIZE:
            raise ValueError(f"Blowfish IV must be {cls.IV_SIZE} bytes")

        start_time = time.perf_counter()

        # Apply PKCS7 padding for 8-byte block size
        padded_data = pad(plaintext, cls.BLOCK_SIZE, style='pkcs7')

        # Encrypt with Blowfish CBC
        cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv=iv)
        ciphertext = cipher.encrypt(padded_data)

        # Compute HMAC-SHA256 over IV + ciphertext
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        tag = h.finalize()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        encrypted_blob = iv + tag + ciphertext
        return encrypted_blob, key, iv, elapsed_ms

    @classmethod
    def decrypt(cls, encrypted_blob: bytes, key: bytes, expected_iv: bytes = None) -> tuple[bytes, float]:
        """
        Verifies HMAC integrity and decrypts Blowfish-CBC ciphertext.
        Returns: (plaintext, elapsed_ms)
        Raises: ValueError on HMAC verification failure or invalid padding/key.
        """
        if len(key) not in range(4, 57):
            raise ValueError("Invalid Blowfish key length")
        if len(encrypted_blob) < cls.IV_SIZE + cls.TAG_SIZE:
            raise ValueError("Ciphertext is too short to be valid")

        start_time = time.perf_counter()

        iv = encrypted_blob[:cls.IV_SIZE]
        tag = encrypted_blob[cls.IV_SIZE:cls.IV_SIZE + cls.TAG_SIZE]
        ciphertext = encrypted_blob[cls.IV_SIZE + cls.TAG_SIZE:]

        if expected_iv and iv != expected_iv:
            raise ValueError("IV mismatch between metadata and payload")

        # Verify HMAC first
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        try:
            h.verify(tag)
        except Exception as e:
            raise ValueError("Ciphertext integrity verification failed (HMAC mismatch / tampered data)") from e

        # Decrypt
        cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv=iv)
        padded_data = cipher.decrypt(ciphertext)

        # Unpad
        plaintext = unpad(padded_data, cls.BLOCK_SIZE, style='pkcs7')

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return plaintext, elapsed_ms

