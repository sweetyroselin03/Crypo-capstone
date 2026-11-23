import base64
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

class EyeDetector:
    """
    Webcam-based eye-region / periocular detector and feature extractor.
    Uses OpenCV Haar Cascades for reliable, high-speed face and eye localization,
    CLAHE preprocessing, and Local Binary Pattern (LBP) texture descriptor extraction.
    Note: This is a webcam-based periocular biometric demonstration, not a medical-grade iris scanner.
    """

    def __init__(self):
        # Load OpenCV Haar Cascades
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def decode_frame(self, frame_b64: str) -> Optional[np.ndarray]:
        """Decode base64 image data into OpenCV BGR image array."""
        try:
            if "," in frame_b64:
                frame_b64 = frame_b64.split(",")[1]
            img_data = base64.b64decode(frame_b64)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    def detect_eye_regions(self, img: np.ndarray) -> List[np.ndarray]:
        """
        Locate face and eye regions, returning cropped eye patches resized to 64x64.
        """
        if img is None:
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))

        cropped_eyes: List[np.ndarray] = []

        if len(faces) == 0:
            # Fallback: search for eyes directly in upper half of image
            h, w = gray.shape
            upper_half = gray[0:int(h * 0.65), :]
            eyes = self.eye_cascade.detectMultiScale(upper_half, scaleFactor=1.1, minNeighbors=3, minSize=(25, 25))
            for (ex, ey, ew, eh) in eyes[:2]:
                eye_roi = upper_half[ey:ey+eh, ex:ex+ew]
                resized = cv2.resize(eye_roi, (64, 64))
                clahe_eye = self.clahe.apply(resized)
                cropped_eyes.append(clahe_eye)
            return cropped_eyes

        # For detected face(s), extract eye ROIs
        for (x, y, w, h) in faces[:1]:
            face_roi = gray[y:y + int(h * 0.65), x:x + w]
            eyes = self.eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
            for (ex, ey, ew, eh) in eyes[:2]:
                eye_roi = face_roi[ey:ey+eh, ex:ex+ew]
                resized = cv2.resize(eye_roi, (64, 64))
                clahe_eye = self.clahe.apply(resized)
                cropped_eyes.append(clahe_eye)

        return cropped_eyes

    @staticmethod
    def compute_lbp(image: np.ndarray) -> np.ndarray:
        """
        Compute Local Binary Pattern (LBP) representation of a 64x64 grayscale patch.
        """
        h, w = image.shape
        lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)

        # 8-neighbor thresholding
        center = image[1:h-1, 1:w-1]
        lbp |= (image[0:h-2, 0:w-2] >= center).astype(np.uint8) << 7
        lbp |= (image[0:h-2, 1:w-1] >= center).astype(np.uint8) << 6
        lbp |= (image[0:h-2, 2:w]   >= center).astype(np.uint8) << 5
        lbp |= (image[1:h-1, 2:w]   >= center).astype(np.uint8) << 4
        lbp |= (image[2:h,   2:w]   >= center).astype(np.uint8) << 3
        lbp |= (image[2:h,   1:w-1] >= center).astype(np.uint8) << 2
        lbp |= (image[2:h,   0:w-2] >= center).astype(np.uint8) << 1
        lbp |= (image[1:h-1, 0:w-2] >= center).astype(np.uint8) << 0

        return lbp

    def extract_feature_vector(self, eye_patch: np.ndarray) -> np.ndarray:
        """
        Generate a 512-dimensional normalized feature vector from eye patch.
        Splits LBP into spatial grid (2x2) with 128 histogram bins each = 512 dimensions.
        """
        lbp = self.compute_lbp(eye_patch)  # 62x62
        h, w = lbp.shape
        mid_h, mid_w = h // 2, w // 2

        # 4 spatial quadrants
        quads = [
            lbp[0:mid_h, 0:mid_w],
            lbp[0:mid_h, mid_w:w],
            lbp[mid_h:h, 0:mid_w],
            lbp[mid_h:h, mid_w:w],
        ]

        feature_vector = []
        for q in quads:
            hist, _ = np.histogram(q.ravel(), bins=128, range=(0, 256))
            feature_vector.extend(hist.astype(np.float32))

        vector = np.array(feature_vector, dtype=np.float32)

        # L2 normalize
        norm = np.linalg.norm(vector)
        if norm > 1e-6:
            vector = vector / norm
        else:
            vector = np.zeros_like(vector)

        return vector

    def process_frame(self, frame_b64: str) -> Dict[str, Any]:
        """
        Process single webcam frame, extract eye patch and feature vector.
        """
        img = self.decode_frame(frame_b64)
        if img is None:
            return {"success": False, "message": "Failed to decode frame image"}

        eye_patches = self.detect_eye_regions(img)
        if not eye_patches:
            return {"success": False, "message": "No eye region detected. Position face towards camera."}

        # Use the clearest eye patch detected
        eye_patch = eye_patches[0]
        feature_vector = self.extract_feature_vector(eye_patch)

        # Approximate openness ratio based on vertical variance
        openness = float(np.std(eye_patch)) / 128.0

        return {
            "success": True,
            "feature_vector": feature_vector.tolist(),
            "openness": openness,
            "eyes_detected": len(eye_patches),
        }
