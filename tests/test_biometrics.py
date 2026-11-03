import unittest
import os
import sys
import time
import numpy as np
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import init_db, SessionLocal, Transfer, BiometricTemplate
from biometric.detect import EyeDetector, QualityError
from biometric.liveness import LivenessTracker
from biometric.features import BiometricFeatureExtractor
from biometric.matcher import BiometricMatcher


class TestBiometricsModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.transfer_id = "tr-bio-test-999"
        db = SessionLocal()
        db.query(Transfer).filter(Transfer.id == self.transfer_id).delete()
        db.query(BiometricTemplate).filter(BiometricTemplate.transfer_id == self.transfer_id).delete()

        t = Transfer(
            id=self.transfer_id,
            original_filename="contract.xlsx",
            file_size_bytes=2048,
            cipher_type="AES",
            encrypted_file_path="data/dummy.enc",
            password_hash="pwd_hash",
            password_salt="pwd_salt",
            qr_payload="qr_payload",
            qr_image_path="data/dummy.png",
            failed_password_attempts=0,
            failed_eye_attempts=0
        )
        db.add(t)
        db.commit()
        db.close()

    def test_quality_check(self):
        # 1. Dark frame should raise QualityError
        dark_img = np.zeros((200, 200, 3), dtype=np.uint8)
        with self.assertRaises(QualityError):
            EyeDetector.check_quality(dark_img, min_brightness=30.0)

        # 2. Blurry frame should raise QualityError
        blurry_img = np.full((200, 200, 3), 120, dtype=np.uint8)
        with self.assertRaises(QualityError):
            EyeDetector.check_quality(blurry_img, min_laplacian_var=30.0)

        # 3. Sharp, well-lit synthetic face/eye frame should pass
        good_img = np.full((200, 200, 3), 128, dtype=np.uint8)
        # Add high-contrast gradient/edges
        good_img[50:150, 50:150] = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
        passed, lap_var, brightness = EyeDetector.check_quality(good_img)
        self.assertTrue(passed)
        self.assertGreater(lap_var, 35.0)

    def test_liveness_blink_tracking(self):
        tracker = LivenessTracker(challenge_type="BLINK")

        # Initial state: Eyes open (EAR = 0.28)
        res1 = tracker.update(ear=0.28)
        self.assertFalse(res1["liveness_passed"])
        self.assertEqual(res1["state"], "EYES_OPEN")

        # Step 2: Blink occurs (EAR drops to 0.14)
        res2 = tracker.update(ear=0.14)
        self.assertFalse(res2["liveness_passed"])
        self.assertEqual(res2["state"], "BLINKING")

        # Step 3: Eyes reopen (EAR rises back to 0.28)
        time.sleep(0.1)  # small realistic delay
        res3 = tracker.update(ear=0.28)
        self.assertTrue(res3["liveness_passed"])
        self.assertEqual(res3["state"], "COMPLETED")

    def test_feature_extraction_and_template_encryption(self):
        # Generate synthetic eye textures
        eye1 = np.random.randint(60, 200, (64, 64), dtype=np.uint8)
        eye2 = np.random.randint(60, 200, (64, 64), dtype=np.uint8)

        embedding = BiometricFeatureExtractor.extract_embedding(eye1, eye2)
        self.assertIsInstance(embedding, np.ndarray)
        # Verify L2 unit norm
        self.assertAlmostEqual(float(np.linalg.norm(embedding)), 1.0, places=4)

        # Test AES-GCM encryption at rest
        enc_blob, nonce = BiometricFeatureExtractor.encrypt_template(embedding)
        self.assertGreater(len(enc_blob), 0)
        self.assertEqual(len(nonce), 12)

        # Decrypt
        decrypted_embedding = BiometricFeatureExtractor.decrypt_template(enc_blob, nonce)
        self.assertEqual(len(decrypted_embedding), len(embedding))
        np.testing.assert_array_almost_equal(embedding, decrypted_embedding, decimal=5)

    def test_matching_same_person_vs_imposter(self):
        np.random.seed(42)
        # Template subject A
        eye_a1 = np.random.randint(80, 180, (64, 64), dtype=np.uint8)
        eye_a2 = np.random.randint(80, 180, (64, 64), dtype=np.uint8)
        emb_a = BiometricFeatureExtractor.extract_embedding(eye_a1, eye_a2)

        # Enroll subject A
        BiometricMatcher.save_enrolled_template(self.transfer_id, emb_a, sample_count=20)

        # Query frame 1: Same subject with slight noise (should MATCH)
        noisy_a1 = np.clip(eye_a1.astype(int) + np.random.randint(-10, 10, (64, 64)), 0, 255).astype(np.uint8)
        noisy_a2 = np.clip(eye_a2.astype(int) + np.random.randint(-10, 10, (64, 64)), 0, 255).astype(np.uint8)
        emb_query_same = BiometricFeatureExtractor.extract_embedding(noisy_a1, noisy_a2)

        match_res = BiometricMatcher.verify_live_scan(self.transfer_id, emb_query_same, threshold=0.90)
        self.assertTrue(match_res["match"])
        self.assertGreaterEqual(match_res["similarity"], 0.90)

        # Query frame 2: Different imposter subject (should FAIL match)
        eye_b1 = np.random.randint(0, 100, (64, 64), dtype=np.uint8)
        eye_b2 = np.random.randint(150, 255, (64, 64), dtype=np.uint8)
        emb_imposter = BiometricFeatureExtractor.extract_embedding(eye_b1, eye_b2)

        imposter_res = BiometricMatcher.verify_live_scan(self.transfer_id, emb_imposter, threshold=0.90)
        self.assertFalse(imposter_res["match"])

    def test_lockout_after_3_failed_attempts(self):
        # Enroll subject
        eye1 = np.random.randint(50, 150, (64, 64), dtype=np.uint8)
        eye2 = np.random.randint(50, 150, (64, 64), dtype=np.uint8)
        emb = BiometricFeatureExtractor.extract_embedding(eye1, eye2)
        BiometricMatcher.save_enrolled_template(self.transfer_id, emb, sample_count=20)

        # Complete imposter embedding (orthogonal noise)
        imposter_emb = np.random.randn(len(emb)).astype(np.float32)
        imposter_emb /= np.linalg.norm(imposter_emb)

        # Attempt 1 -> Fail (2 left)
        res1 = BiometricMatcher.verify_live_scan(self.transfer_id, imposter_emb, threshold=0.85)
        self.assertFalse(res1["match"])
        self.assertFalse(res1["locked"])
        self.assertEqual(res1["attempts_left"], 2)

        # Attempt 2 -> Fail (1 left)
        res2 = BiometricMatcher.verify_live_scan(self.transfer_id, imposter_emb, threshold=0.85)
        self.assertFalse(res2["match"])
        self.assertFalse(res2["locked"])
        self.assertEqual(res2["attempts_left"], 1)

        # Attempt 3 -> Fail & LOCK (0 left, locked = True)
        res3 = BiometricMatcher.verify_live_scan(self.transfer_id, imposter_emb, threshold=0.85)
        self.assertFalse(res3["match"])
        self.assertTrue(res3["locked"])
        self.assertEqual(res3["attempts_left"], 0)
        self.assertIn("locked", res3["message"].lower())


if __name__ == "__main__":
    unittest.main()
