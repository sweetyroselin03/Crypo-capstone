import os
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes, hmac
from cryptography.hazmat.backends import default_backend


class AESCipher:
    """
    AES-128-CBC encryption and decryption with PKCS7 padding and HMAC-SHA256
    Encrypt-then-MAC integrity protection.
    """

    KEY_SIZE = 16  # 128-bit key
    IV_SIZE = 16   # 128-bit IV
    TAG_SIZE = 32  # SHA-256 HMAC (256-bit)

    @classmethod
    def generate_key(cls) -> bytes:
        return os.urandom(cls.KEY_SIZE)

    @classmethod
    def generate_iv(cls) -> bytes:
        return os.urandom(cls.IV_SIZE)

    @classmethod
    def encrypt(cls, plaintext: bytes, key: bytes = None, iv: bytes = None) -> tuple[bytes, bytes, bytes, float]:
        """
        Encrypts plaintext with AES-128-CBC and computes HMAC-SHA256 over IV + ciphertext.
        Returns: (encrypted_blob, key, iv, elapsed_ms)
        Format of encrypted_blob: IV (16B) + HMAC_TAG (32B) + CIPHERTEXT
        """
        if not key:
            key = cls.generate_key()
        if len(key) != cls.KEY_SIZE:
            raise ValueError(f"AES key must be {cls.KEY_SIZE} bytes")
        if not iv:
            iv = cls.generate_iv()
        if len(iv) != cls.IV_SIZE:
            raise ValueError(f"AES IV must be {cls.IV_SIZE} bytes")

        start_time = time.perf_counter()

        # Apply PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()

        # Encrypt with AES-CBC
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Compute HMAC-SHA256 over IV + ciphertext (Encrypt-then-MAC)
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        tag = h.finalize()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        encrypted_blob = iv + tag + ciphertext
        return encrypted_blob, key, iv, elapsed_ms

    @classmethod
    def decrypt(cls, encrypted_blob: bytes, key: bytes, expected_iv: bytes = None) -> tuple[bytes, float]:
        """
        Verifies HMAC integrity and decrypts AES-128-CBC ciphertext.
        Returns: (plaintext, elapsed_ms)
        Raises: ValueError on HMAC verification failure or invalid padding/key.
        """
        if len(key) != cls.KEY_SIZE:
            raise ValueError(f"AES key must be {cls.KEY_SIZE} bytes")
        if len(encrypted_blob) < cls.IV_SIZE + cls.TAG_SIZE:
            raise ValueError("Ciphertext is too short to be valid")

        start_time = time.perf_counter()

        iv = encrypted_blob[:cls.IV_SIZE]
        tag = encrypted_blob[cls.IV_SIZE:cls.IV_SIZE + cls.TAG_SIZE]
        ciphertext = encrypted_blob[cls.IV_SIZE + cls.TAG_SIZE:]

        if expected_iv and iv != expected_iv:
            raise ValueError("IV mismatch between metadata and payload")

        # Verify HMAC first to detect tampering
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        try:
            h.verify(tag)
        except Exception as e:
            raise ValueError("Ciphertext integrity verification failed (HMAC mismatch / tampered data)") from e

        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return plaintext, elapsed_ms

