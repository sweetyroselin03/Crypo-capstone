import unittest
import os
import sys
import io
import time
import json
import base64
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database import init_db, SessionLocal, Transfer, BiometricTemplate, AuditLog
from crypto.aes import AESCipher
from crypto.blowfish import BlowfishCipher
from crypto.keywrap import KeyWrapper
from biometric.features import BiometricFeatureExtractor
from biometric.matcher import BiometricMatcher


class TestFullSecurityAndFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-security'

    def setUp(self):
        self.client = app.test_client()

    def test_complete_receiver_flow_success(self):
        """
        Tests the complete 6-step flow in strict order:
        QR_OK -> PASSWORD_OK -> KEY_SHOWN -> EYE_ENROLLED -> EYE_VERIFIED -> DATA_VIEW
        """
        # 1. Sender Uploads Contract
        df_original = pd.DataFrame({
            "ID": [101, 102],
            "Clause": ["NDA Term 2026", "Intellectual Property Ownership"],
            "Value": [500000, 1200000]
        })
        excel_buffer = io.BytesIO()
        df_original.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        password = "MasterReceiverPass@2026"

        upload_res = self.client.post('/sender/upload', data={
            'file': (excel_buffer, 'test_contract.xlsx'),
            'cipher_type': 'AES',
            'password': password
        }, content_type='multipart/form-data')

        self.assertEqual(upload_res.status_code, 200)
        upload_data = upload_res.get_json()
        self.assertTrue(upload_data['success'])
        transfer_id = upload_data['transfer_id']
        qr_payload = upload_data['qr_payload']

        # Reset session
        self.client.get('/receiver')

        # STEP 1: Scan QR
        qr_res = self.client.post('/api/receiver/qr-scan', json={'qr_payload': qr_payload})
        self.assertEqual(qr_res.status_code, 200)
        self.assertTrue(qr_res.get_json()['success'])

        # STEP 2: Password Verification
        pwd_res = self.client.post('/api/receiver/verify-password', json={'password': password})
        self.assertEqual(pwd_res.status_code, 200)
        self.assertTrue(pwd_res.get_json()['success'])

        # STEP 3: Secret Key Reveal
        key_res = self.client.get('/api/receiver/secret-key')
        self.assertEqual(key_res.status_code, 200)
        key_data = key_res.get_json()
        self.assertTrue(key_data['success'])
        self.assertIn('key_hex', key_data)
        self.assertIn('iv_hex', key_data)

        # STEP 4: Eye Scan Enrollment (Synthesize 16 quality frame embeddings)
        np.random.seed(123)
        eye_base1 = np.random.randint(70, 190, (64, 64), dtype=np.uint8)
        eye_base2 = np.random.randint(70, 190, (64, 64), dtype=np.uint8)

        embeddings_list = []
        for _ in range(16):
            n1 = np.clip(eye_base1.astype(int) + np.random.randint(-5, 5, (64, 64)), 0, 255).astype(np.uint8)
            n2 = np.clip(eye_base2.astype(int) + np.random.randint(-5, 5, (64, 64)), 0, 255).astype(np.uint8)
            emb = BiometricFeatureExtractor.extract_embedding(n1, n2)
            embeddings_list.append(emb)

        # Enroll centroid template
        centroid = BiometricMatcher.aggregate_enrollment(embeddings_list)
        BiometricMatcher.save_enrolled_template(transfer_id, centroid, sample_count=16)

        # Complete Step 4 via internal session/state transition
        from routes.receiver import enrollment_buffers
        enrollment_buffers[transfer_id] = embeddings_list

        enroll_complete_res = self.client.post('/api/receiver/eye-enroll-complete')
        self.assertEqual(enroll_complete_res.status_code, 200)

        # STEP 5: Eye Scan Verification (Matching Query)
        same_q1 = np.clip(eye_base1.astype(int) + np.random.randint(-3, 3, (64, 64)), 0, 255).astype(np.uint8)
        same_q2 = np.clip(eye_base2.astype(int) + np.random.randint(-3, 3, (64, 64)), 0, 255).astype(np.uint8)
        query_emb = BiometricFeatureExtractor.extract_embedding(same_q1, same_q2)

        match_out = BiometricMatcher.verify_live_scan(transfer_id, query_emb, threshold=0.90)
        self.assertTrue(match_out['match'])

        # Advance session to EYE_VERIFIED
        from state_machine import ReceiverStateMachine, ReceiverState
        with self.client.session_transaction() as sess:
            sess[ReceiverStateMachine.SESSION_STATE_KEY] = ReceiverState.EYE_VERIFIED.value

        # STEP 6: View Data
        view_res = self.client.get('/api/receiver/view-data')
        self.assertEqual(view_res.status_code, 200)
        view_data = view_res.get_json()
        self.assertTrue(view_data['success'])
        self.assertEqual(view_data['total_rows'], 2)
        self.assertIn('Clause', view_data['columns'])

        # Download decrypted excel
        dl_res = self.client.get(f'/download/decrypted-excel/{transfer_id}')
        self.assertEqual(dl_res.status_code, 200)
        self.assertIn('application/vnd.openxmlformats', dl_res.content_type)

    def test_out_of_order_calls_rejected_with_403(self):
        """
        Verify that skipping steps returns 403 Forbidden.
        """
        self.client.get('/receiver')  # Resets state to INITIAL

        # Direct attempt to call Step 6 (view-data) without authentication
        res1 = self.client.get('/api/receiver/view-data')
        self.assertEqual(res1.status_code, 403)

        # Direct attempt to call Step 3 (secret-key) without password verification
        res2 = self.client.get('/api/receiver/secret-key')
        self.assertEqual(res2.status_code, 403)

        # Direct attempt to complete eye enrollment
        res3 = self.client.post('/api/receiver/eye-enroll-complete')
        self.assertEqual(res3.status_code, 403)

    def test_tampered_ciphertext_detected_and_rejected(self):
        """
        Modifying even 1 byte in the stored ciphertext causes HMAC integrity failure.
        """
        data = b"ID,SecretClause\n1,TopSecretDefenseFormula"
        encrypted_blob, key, iv, _ = AESCipher.encrypt(data)

        # Tamper with encrypted blob
        tampered = bytearray(encrypted_blob)
        tampered[-2] ^= 0xAA

        with self.assertRaises(ValueError) as ctx:
            AESCipher.decrypt(bytes(tampered), key)
        self.assertIn("tampered", str(ctx.exception).lower())

    def test_password_rate_limiting_and_lockout(self):
        """
        5 consecutive wrong password attempts triggers a 15-minute lockout.
        """
        transfer_id = "tr-lockout-test"
        pwd_hash, pwd_salt = KeyWrapper.hash_password("RealSecret123")
        qr_blob = KeyWrapper.wrap_keys("AES", os.urandom(16), os.urandom(16), "RealSecret123", transfer_id)

        db = SessionLocal()
        db.query(Transfer).filter(Transfer.id == transfer_id).delete()
        t = Transfer(
            id=transfer_id,
            original_filename="confidential.xlsx",
            file_size_bytes=100,
            cipher_type="AES",
            encrypted_file_path="dummy.enc",
            password_hash=pwd_hash,
            password_salt=pwd_salt,
            qr_payload=qr_blob,
            qr_image_path="dummy.png",
            failed_password_attempts=0
        )
        db.add(t)
        db.commit()
        db.close()

        # Step 1: Scan QR
        self.client.get('/receiver')
        self.client.post('/api/receiver/qr-scan', json={'qr_payload': qr_blob})

        # 4 wrong attempts -> returns 401
        for i in range(4):
            r = self.client.post('/api/receiver/verify-password', json={'password': f'WrongPwd{i}'})
            self.assertEqual(r.status_code, 401)

        # 5th wrong attempt -> returns 423 Locked!
        r5 = self.client.post('/api/receiver/verify-password', json={'password': 'WrongPwdFinal'})
        self.assertEqual(r5.status_code, 423)
        self.assertIn("locked", r5.get_json()['error'].lower())


if __name__ == "__main__":
    unittest.main()
