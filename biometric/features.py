import os
import json
import numpy as np
import cv2
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class BiometricFeatureExtractor:
    """
    Extracts discriminative biometric feature embeddings from normalized periocular/iris regions.
    Uses:
    1. Uniform Local Binary Pattern (LBP) spatial grid histograms.
    2. Concentric iris annular ring statistics (radial gradient & density).
    3. Multi-scale gradient orientation descriptors.
    Outputs an L2-normalized 1D feature embedding vector.
    """

    DEFAULT_SECRET_KEY = "BIOMETRIC_CAPSTONE_ENCRYPTION_KEY_2026_SECURE_VAULT"

    @staticmethod
    def _compute_lbp(gray_img: np.ndarray) -> np.ndarray:
        """
        Computes 8-neighbor basic Local Binary Pattern (LBP) image.
        """
        h, w = gray_img.shape
        lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)

        center = gray_img[1:-1, 1:-1]
        neighbors = [
            gray_img[0:-2, 0:-2],  # Top-left
            gray_img[0:-2, 1:-1],  # Top
            gray_img[0:-2, 2:],    # Top-right
            gray_img[1:-1, 2:],    # Right
            gray_img[2:, 2:],      # Bottom-right
            gray_img[2:, 1:-1],    # Bottom
            gray_img[2:, 0:-2],    # Bottom-left
            gray_img[1:-1, 0:-2],  # Left
        ]

        for power, neighbor in enumerate(neighbors):
            lbp += ((neighbor >= center).astype(np.uint8)) << power

        return lbp

    @classmethod
    def _extract_lbp_grid_hist(cls, eye_crop: np.ndarray, grid_r: int = 4, grid_c: int = 4, bins: int = 16) -> np.ndarray:
        """
        Extracts spatial histogram of LBP across a grid_r x grid_c grid.
        """
        lbp = cls._compute_lbp(eye_crop)
        h, w = lbp.shape
        cell_h, cell_w = h // grid_r, w // grid_c
        features = []

        for r in range(grid_r):
            for c in range(grid_c):
                cell = lbp[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w]
                hist, _ = np.histogram(cell, bins=bins, range=(0, 256), density=False)
                # Cell normalization
                norm = np.linalg.norm(hist) + 1e-6
                features.append(hist / norm)

        return np.concatenate(features)

    @classmethod
    def _extract_iris_ring_stats(cls, eye_crop: np.ndarray, rings: int = 8) -> np.ndarray:
        """
        Extracts concentric annular statistics around the center of the eye crop.
        """
        h, w = eye_crop.shape
        cy, cx = h // 2, w // 2
        y, x = np.ogrid[:h, :w]
        distances = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        max_radius = min(cx, cy) * 0.9
        radii = np.linspace(2, max_radius, rings + 1)
        stats = []

        for i in range(rings):
            mask = (distances >= radii[i]) & (distances < radii[i + 1])
            pixels = eye_crop[mask]
            if len(pixels) > 0:
                stats.append(float(np.mean(pixels)) / 255.0)
                stats.append(float(np.std(pixels)) / 128.0)
                # Max and min contrast
                stats.append(float(np.max(pixels) - np.min(pixels)) / 255.0)
            else:
                stats.extend([0.0, 0.0, 0.0])

        return np.array(stats, dtype=np.float32)

    @classmethod
    def _extract_spatial_blocks(cls, eye_crop: np.ndarray, grid=(4, 4)) -> np.ndarray:
        """
        Extracts regional mean and variance across spatial grid cells.
        """
        h, w = eye_crop.shape
        gh, gw = grid
        ch, cw = h // gh, w // gw
        stats = []
        for r in range(gh):
            for c in range(gw):
                block = eye_crop[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
                stats.append(float(np.mean(block)) / 255.0)
                stats.append(float(np.std(block)) / 128.0)
        return np.array(stats, dtype=np.float32)

    @classmethod
    def extract_embedding(cls, left_eye: np.ndarray, right_eye: np.ndarray) -> np.ndarray:
        """
        Extracts comprehensive biometric feature embedding from both normalized eyes.
        Returns: 1D L2-normalized float32 numpy array.
        """
        # Left eye descriptors
        left_lbp = cls._extract_lbp_grid_hist(left_eye, grid_r=4, grid_c=4, bins=16)
        left_rings = cls._extract_iris_ring_stats(left_eye, rings=8)
        left_blocks = cls._extract_spatial_blocks(left_eye, grid=(4, 4))

        # Right eye descriptors
        right_lbp = cls._extract_lbp_grid_hist(right_eye, grid_r=4, grid_c=4, bins=16)
        right_rings = cls._extract_iris_ring_stats(right_eye, rings=8)
        right_blocks = cls._extract_spatial_blocks(right_eye, grid=(4, 4))

        combined = np.concatenate([
            left_lbp * 0.4,
            left_rings * 1.5,
            left_blocks * 1.0,
            right_lbp * 0.4,
            right_rings * 1.5,
            right_blocks * 1.0
        ]).astype(np.float32)

        # Mean centering to enhance intra-class vs inter-class discrimination
        combined = combined - np.mean(combined)

        # L2 unit normalization
        norm = np.linalg.norm(combined)
        if norm > 1e-6:
            combined = combined / norm

        return combined

    @classmethod
    def _get_encryption_key(cls) -> bytes:
        secret = os.getenv("BIOMETRIC_SECRET_KEY", cls.DEFAULT_SECRET_KEY)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"BIOMETRIC_VAULT_SALT_STATIC",
            iterations=100_000,
            backend=default_backend()
        )
        return kdf.derive(secret.encode('utf-8'))

    @classmethod
    def encrypt_template(cls, embedding: np.ndarray) -> tuple[bytes, bytes]:
        """
        Encrypts biometric template embedding at rest using AES-256-GCM.
        Returns: (ciphertext_blob, nonce)
        """
        raw_bytes = embedding.astype(np.float32).tobytes()
        key = cls._get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        encrypted_blob = aesgcm.encrypt(nonce, raw_bytes, b"BIOMETRIC_TEMPLATE_AAD")
        return encrypted_blob, nonce

    @classmethod
    def decrypt_template(cls, encrypted_blob: bytes, nonce: bytes) -> np.ndarray:
        """
        Decrypts biometric template from rest storage.
        Returns: 1D float32 numpy array embedding.
        """
        key = cls._get_encryption_key()
        aesgcm = AESGCM(key)
        raw_bytes = aesgcm.decrypt(nonce, encrypted_blob, b"BIOMETRIC_TEMPLATE_AAD")
        embedding = np.frombuffer(raw_bytes, dtype=np.float32)
        return embedding
