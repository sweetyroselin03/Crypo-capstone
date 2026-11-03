import unittest
import os
import sys
import base64

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto.aes import AESCipher
from crypto.blowfish import BlowfishCipher
from crypto.keywrap import KeyWrapper


class TestCryptoCore(unittest.TestCase):

    def test_aes_round_trip(self):
        sample_data = b"ID,Name,Salary,Department\n1,Alice,85000,Engineering\n2,Bob,72000,Finance"
        blob, key, iv, enc_time = AESCipher.encrypt(sample_data)
        self.assertEqual(len(key), 16)
        self.assertEqual(len(iv), 16)
        self.assertGreater(len(blob), len(sample_data))
        self.assertGreater(enc_time, 0.0)

        decrypted, dec_time = AESCipher.decrypt(blob, key, expected_iv=iv)
        self.assertEqual(decrypted, sample_data)
        self.assertGreater(dec_time, 0.0)

    def test_aes_tampering_detected(self):
        sample_data = b"Confidential financial statement data"
        blob, key, iv, _ = AESCipher.encrypt(sample_data)

        # Tamper with the last byte of ciphertext
        tampered = bytearray(blob)
        tampered[-1] ^= 0x5A

        with self.assertRaises(ValueError) as ctx:
            AESCipher.decrypt(bytes(tampered), key)
        self.assertIn("tampered", str(ctx.exception).lower())

    def test_blowfish_round_trip(self):
        sample_data = b"Project Capstone: Secure Key Exchange Blowfish Test Data"
        blob, key, iv, enc_time = BlowfishCipher.encrypt(sample_data)
        self.assertEqual(len(key), 8)
        self.assertEqual(len(iv), 8)
        self.assertGreater(len(blob), len(sample_data))
        self.assertGreater(enc_time, 0.0)

        decrypted, dec_time = BlowfishCipher.decrypt(blob, key, expected_iv=iv)
        self.assertEqual(decrypted, sample_data)

    def test_blowfish_tampering_detected(self):
        sample_data = b"Secret Legal Clause: Non-disclosure agreement"
        blob, key, iv, _ = BlowfishCipher.encrypt(sample_data)

        tampered = bytearray(blob)
        tampered[-1] ^= 0xFF

        with self.assertRaises(ValueError) as ctx:
            BlowfishCipher.decrypt(bytes(tampered), key)
        self.assertIn("tampered", str(ctx.exception).lower())

    def test_password_hashing_and_verification(self):
        password = "SecurePassword123!"
        stored_hash, stored_salt = KeyWrapper.hash_password(password)

        self.assertTrue(KeyWrapper.verify_password(password, stored_hash, stored_salt))
        self.assertFalse(KeyWrapper.verify_password("WrongPassword!", stored_hash, stored_salt))

    def test_key_wrapping_round_trip(self):
        transfer_id = "tr-test-12345"
        raw_key = os.urandom(16)
        raw_iv = os.urandom(16)
        password = "CorrectPassphrase#456"

        qr_blob = KeyWrapper.wrap_keys("AES", raw_key, raw_iv, password, transfer_id)
        self.assertIsInstance(qr_blob, str)

        # Unwrap with correct password
        unwrapped = KeyWrapper.unwrap_keys(qr_blob, password)
        self.assertEqual(unwrapped["cipher"], "AES")
        self.assertEqual(unwrapped["raw_key"], raw_key)
        self.assertEqual(unwrapped["raw_iv"], raw_iv)
        self.assertEqual(unwrapped["transfer_id"], transfer_id)

    def test_key_wrapping_wrong_password_fails(self):
        transfer_id = "tr-test-99999"
        raw_key = os.urandom(16)
        raw_iv = os.urandom(16)
        password = "SenderSecretPassword"

        qr_blob = KeyWrapper.wrap_keys("AES", raw_key, raw_iv, password, transfer_id)

        with self.assertRaises(ValueError) as ctx:
            KeyWrapper.unwrap_keys(qr_blob, "AttackerWrongPassword")
        self.assertIn("incorrect password", str(ctx.exception).lower())

    def test_crypto_performance_comparison(self):
        # 100 KB payload for benchmark
        payload = b"X" * (100 * 1024)
        aes_blob, aes_k, aes_iv, aes_enc_ms = AESCipher.encrypt(payload)
        bf_blob, bf_k, bf_iv, bf_enc_ms = BlowfishCipher.encrypt(payload)

        # Throughput = file size KB / (time in seconds)
        size_kb = len(payload) / 1024.0
        aes_throughput_kb_s = size_kb / (aes_enc_ms / 1000.0) if aes_enc_ms > 0 else 0
        bf_throughput_kb_s = size_kb / (bf_enc_ms / 1000.0) if bf_enc_ms > 0 else 0

        self.assertGreater(aes_throughput_kb_s, 0)
        self.assertGreater(bf_throughput_kb_s, 0)
        print(f"\n[Benchmark 100KB] AES: {aes_enc_ms:.2f}ms ({aes_throughput_kb_s:.1f} KB/s) | Blowfish: {bf_enc_ms:.2f}ms ({bf_throughput_kb_s:.1f} KB/s)")


if __name__ == "__main__":
    unittest.main()
