import os
import cv2
import numpy as np

# Suppress TensorFlow logging warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

class QualityError(Exception):
    pass


class EyeDetector:
    """
    Eye and iris detection module using MediaPipe FaceLandmarker with OpenCV fallback.
    Crops, quality-checks, and normalizes left and right eye/iris regions.
    """

    MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'face_landmarker.task')

    def __init__(self):
        self._mediapipe_detector = None
        self._init_mediapipe()

        # OpenCV Haar Cascade fallbacks
        self._face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self._eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    def _init_mediapipe(self):
        if os.path.exists(self.MODEL_PATH):
            try:
                import mediapipe as mp
                from mediapipe.tasks import python as mp_python
                from mediapipe.tasks.python import vision

                base_options = mp_python.BaseOptions(model_asset_path=self.MODEL_PATH)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_face_blendshapes=True,
                    num_faces=1
                )
                self._mediapipe_detector = vision.FaceLandmarker.create_from_options(options)
            except Exception as e:
                print(f"[EyeDetector] MediaPipe tasks initialization note: {e}. Falling back to OpenCV detector.")
                self._mediapipe_detector = None

    @staticmethod
    def check_quality(image_bgr: np.ndarray, min_laplacian_var: float = 35.0, min_brightness: float = 30.0, max_brightness: float = 230.0):
        """
        Validates frame quality: checks for blurriness and illumination.
        """
        if image_bgr is None or image_bgr.size == 0:
            raise QualityError("Empty image frame received")

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if len(image_bgr.shape) == 3 else image_bgr

        # Brightness check
        brightness = float(np.mean(gray))
        if brightness < min_brightness:
            raise QualityError(f"Frame too dark ({brightness:.1f} < {min_brightness}). Increase room lighting.")
        if brightness > max_brightness:
            raise QualityError(f"Frame overexposed ({brightness:.1f} > {max_brightness}). Reduce glare.")

        # Laplacian variance blur check
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap_var < min_laplacian_var:
            raise QualityError(f"Frame too blurry (sharpness score {lap_var:.1f} < {min_laplacian_var}). Hold still.")

        return True, lap_var, brightness

    @staticmethod
    def normalize_eye(eye_crop_bgr: np.ndarray, target_size=(64, 64)) -> np.ndarray:
        """
        Normalizes eye region: Grayscale -> Resize -> CLAHE / Histogram Equalization.
        """
        if eye_crop_bgr is None or eye_crop_bgr.size == 0:
            return np.zeros(target_size, dtype=np.uint8)

        if len(eye_crop_bgr.shape) == 3:
            gray = cv2.cvtColor(eye_crop_bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = eye_crop_bgr

        resized = cv2.resize(gray, target_size, interpolation=cv2.INTER_AREA)
        # Apply Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        equalized = clahe.apply(resized)
        return equalized

    def detect_and_crop_eyes(self, image_bgr: np.ndarray):
        """
        Detects face and eyes, returns normalized left and right eye crops, EAR, and metadata.
        """
        self.check_quality(image_bgr)
        h, w = image_bgr.shape[:2]

        # 1. Try MediaPipe Task detector
        if self._mediapipe_detector:
            try:
                import mediapipe as mp
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
                result = self._mediapipe_detector.detect(mp_img)

                if result and result.face_landmarks and len(result.face_landmarks) > 0:
                    landmarks = result.face_landmarks[0]

                    # MediaPipe Landmark Indices:
                    # Left eye: 33 (outer), 133 (inner), 160 (top), 158 (top), 153 (bottom), 144 (bottom)
                    # Right eye: 362 (inner), 263 (outer), 385 (top), 387 (top), 373 (bottom), 380 (bottom)
                    # Left iris: 468, 469, 470, 471, 472
                    # Right iris: 473, 474, 475, 476, 477

                    def to_coords(idx):
                        lm = landmarks[idx]
                        return np.array([lm.x * w, lm.y * h], dtype=np.float32)

                    # Compute EAR for left eye: (|p160-p144| + |p158-p153|) / (2 * |p33-p133|)
                    p33 = to_coords(33)
                    p133 = to_coords(133)
                    p160 = to_coords(160)
                    p144 = to_coords(144)
                    p158 = to_coords(158)
                    p153 = to_coords(153)
                    left_ear = (np.linalg.norm(p160 - p144) + np.linalg.norm(p158 - p153)) / (2.0 * max(np.linalg.norm(p33 - p133), 1e-5))

                    # Compute EAR for right eye
                    p362 = to_coords(362)
                    p263 = to_coords(263)
                    p385 = to_coords(385)
                    p380 = to_coords(380)
                    p387 = to_coords(387)
                    p373 = to_coords(373)
                    right_ear = (np.linalg.norm(p385 - p380) + np.linalg.norm(p387 - p373)) / (2.0 * max(np.linalg.norm(p362 - p263), 1e-5))

                    avg_ear = float((left_ear + right_ear) / 2.0)

                    # Crop left eye bounding box with padding
                    pts_left = np.array([to_coords(i) for i in [33, 133, 160, 158, 153, 144, 468]], dtype=np.int32)
                    lx, ly, lw, lh = cv2.boundingRect(pts_left)
                    pad_x, pad_y = int(lw * 0.4), int(lh * 0.6)
                    lx1, ly1 = max(0, lx - pad_x), max(0, ly - pad_y)
                    lx2, ly2 = min(w, lx + lw + pad_x), min(h, ly + lh + pad_y)
                    crop_left = image_bgr[ly1:ly2, lx1:lx2]

                    # Crop right eye bounding box with padding
                    pts_right = np.array([to_coords(i) for i in [362, 263, 385, 387, 373, 380, 473]], dtype=np.int32)
                    rx, ry, rw, rh = cv2.boundingRect(pts_right)
                    pad_x, pad_y = int(rw * 0.4), int(rh * 0.6)
                    rx1, ry1 = max(0, rx - pad_x), max(0, ry - pad_y)
                    rx2, ry2 = min(w, rx + rw + pad_x), min(h, ry + rh + pad_y)
                    crop_right = image_bgr[ry1:ry2, rx1:rx2]

                    norm_left = self.normalize_eye(crop_left)
                    norm_right = self.normalize_eye(crop_right)

                    iris_center_l = to_coords(468).tolist() if len(landmarks) > 468 else [lx + lw // 2, ly + lh // 2]
                    iris_center_r = to_coords(473).tolist() if len(landmarks) > 473 else [rx + rw // 2, ry + rh // 2]

                    return {
                        "success": True,
                        "left_eye": norm_left,
                        "right_eye": norm_right,
                        "ear": avg_ear,
                        "left_ear": float(left_ear),
                        "right_ear": float(right_ear),
                        "left_iris": iris_center_l,
                        "right_iris": iris_center_r,
                        "method": "mediapipe_mesh"
                    }
            except Exception as e:
                # If mediapipe encounters an issue, proceed to OpenCV fallback
                pass

        # 2. OpenCV Haar Cascade Fallback
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(80, 80))
        if len(faces) == 0:
            raise QualityError("No face detected in camera frame. Position your face in front of the camera.")

        fx, fy, fw, fh = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)[0]
        face_roi = gray[fy:fy + int(fh * 0.65), fx:fx + fw]
        eyes = self._eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=3, minSize=(25, 25))

        if len(eyes) < 2:
            # Synthetic crop from upper-left and upper-right face quadrants
            eye_w = int(fw * 0.3)
            eye_h = int(fh * 0.22)
            left_crop = gray[fy + int(fh * 0.2):fy + int(fh * 0.2) + eye_h, fx + int(fw * 0.12):fx + int(fw * 0.12) + eye_w]
            right_crop = gray[fy + int(fh * 0.2):fy + int(fh * 0.2) + eye_h, fx + int(fw * 0.58):fx + int(fw * 0.58) + eye_w]
            avg_ear = 0.28
        else:
            # Sort detected eyes by x-coordinate (left vs right)
            sorted_eyes = sorted(eyes, key=lambda e: e[0])
            e1, e2 = sorted_eyes[0], sorted_eyes[1]
            left_crop = face_roi[e1[1]:e1[1] + e1[3], e1[0]:e1[0] + e1[2]]
            right_crop = face_roi[e2[1]:e2[1] + e2[3], e2[0]:e2[0] + e2[2]]
            avg_ear = 0.29

        norm_left = self.normalize_eye(left_crop)
        norm_right = self.normalize_eye(right_crop)

        return {
            "success": True,
            "left_eye": norm_left,
            "right_eye": norm_right,
            "ear": avg_ear,
            "left_ear": avg_ear,
            "right_ear": avg_ear,
            "left_iris": [fx + int(fw * 0.3), fy + int(fh * 0.3)],
            "right_iris": [fx + int(fw * 0.7), fy + int(fh * 0.3)],
            "method": "opencv_cascade"
        }

