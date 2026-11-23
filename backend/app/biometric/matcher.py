import json
import numpy as np
from typing import List, Dict, Any, Optional
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

class BiometricMatcher:
    """
    Computes cosine similarity between 512-dimensional normalized feature vectors
    and manages encrypted template storage.
    """

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between two feature vectors."""
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    @staticmethod
    def aggregate_enrollment_template(feature_vectors: List[List[float]]) -> List[float]:
        """
        Aggregate 15-20 frame vectors into an enrolled master template
        by mean pooling and L2 normalization.
        """
        if not feature_vectors:
            raise ValueError("No feature vectors provided for enrollment")

        arr = np.array(feature_vectors, dtype=np.float32)
        mean_vector = np.mean(arr, axis=0)

        norm = np.linalg.norm(mean_vector)
        if norm > 1e-6:
            mean_vector = mean_vector / norm

        return mean_vector.tolist()

    @staticmethod
    def verify(enrolled_vector: List[float], live_vector: List[float], threshold: float = 0.90) -> Dict[str, Any]:
        """
        Match live vector against enrolled template.
        Returns match status, similarity score, and message.
        """
        v_enrolled = np.array(enrolled_vector, dtype=np.float32)
        v_live = np.array(live_vector, dtype=np.float32)

        score = BiometricMatcher.cosine_similarity(v_enrolled, v_live)
        match_passed = bool(score >= threshold)

        return {
            "match_passed": match_passed,
            "similarity_score": round(score, 4),
            "threshold": threshold,
            "message": "Biometric eye verification successful" if match_passed else f"Eye similarity score ({score:.2f}) below threshold ({threshold:.2f})"
        }

    @staticmethod
    def encrypt_template(template_vector: List[float], key: bytes) -> str:
        """Encrypt template JSON with AES-256-CBC for secure database storage."""
        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        data = json.dumps(template_vector).encode("utf-8")
        ciphertext = cipher.encrypt(pad(data, 16))
        return json.dumps({
            "iv": iv.hex(),
            "data": ciphertext.hex()
        })

    @staticmethod
    def decrypt_template(encrypted_str: str, key: bytes) -> List[float]:
        """Decrypt stored template JSON."""
        obj = json.loads(encrypted_str)
        iv = bytes.fromhex(obj["iv"])
        ciphertext = bytes.fromhex(obj["data"])
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decrypted = unpad(cipher.decrypt(ciphertext), 16)
        return json.loads(decrypted.decode("utf-8"))
