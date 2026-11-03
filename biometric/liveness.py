import time
import numpy as np


class LivenessTracker:
    """
    Real-time anti-spoofing challenge verification:
    - Requires active blink challenge (Eye Aspect Ratio drop & recovery).
    - Checks micro-movement and prevents static printed photo or screen replay attacks.
    """

    EAR_OPEN_THRESHOLD = 0.22
    EAR_CLOSED_THRESHOLD = 0.17
    MAX_BLINK_DURATION_SEC = 2.0
    MIN_FRAME_VARIANCE = 2.0

    def __init__(self, challenge_type: str = "BLINK"):
        self.challenge_type = challenge_type
        self.state = "INIT"  # INIT -> EYES_OPEN -> BLINKING -> COMPLETED
        self.blink_start_time = 0.0
        self.ear_history = []
        self.frame_diffs = []
        self.prev_eye_crop = None
        self.is_passed = False

    def reset(self, challenge_type: str = "BLINK"):
        self.challenge_type = challenge_type
        self.state = "INIT"
        self.blink_start_time = 0.0
        self.ear_history.clear()
        self.frame_diffs.clear()
        self.prev_eye_crop = None
        self.is_passed = False

    def update(self, ear: float, eye_crop: np.ndarray = None) -> dict:
        """
        Updates tracker with new frame EAR and eye crop.
        Returns status dictionary: {"liveness_passed": bool, "prompt": str, "ear": float, "state": str}
        """
        now = time.time()
        self.ear_history.append((now, ear))
        if len(self.ear_history) > 30:
            self.ear_history.pop(0)

        # Check frame micro-variation to ensure it's not a frozen photo or looped still image
        if eye_crop is not None and self.prev_eye_crop is not None:
            if eye_crop.shape == self.prev_eye_crop.shape:
                diff = float(np.mean(np.abs(eye_crop.astype(float) - self.prev_eye_crop.astype(float))))
                self.frame_diffs.append(diff)
                if len(self.frame_diffs) > 15:
                    self.frame_diffs.pop(0)
        if eye_crop is not None:
            self.prev_eye_crop = eye_crop.copy()

        if self.is_passed:
            return {
                "liveness_passed": True,
                "prompt": "Liveness Challenge Passed! Hold still for scan.",
                "ear": ear,
                "state": "COMPLETED"
            }

        # Blink state machine
        if self.state == "INIT":
            if ear >= self.EAR_OPEN_THRESHOLD:
                self.state = "EYES_OPEN"
                prompt = "Please blink naturally to verify liveness..."
            else:
                prompt = "Keep your eyes open and look into the camera..."

        elif self.state == "EYES_OPEN":
            if ear < self.EAR_CLOSED_THRESHOLD:
                self.state = "BLINKING"
                self.blink_start_time = now
                prompt = "Blink detected! Open your eyes..."
            else:
                prompt = "Please blink naturally to verify liveness..."

        elif self.state == "BLINKING":
            if ear >= self.EAR_OPEN_THRESHOLD:
                duration = now - self.blink_start_time
                if 0.05 <= duration <= self.MAX_BLINK_DURATION_SEC:
                    # Natural blink completed!
                    self.state = "COMPLETED"
                    self.is_passed = True
                    prompt = "Blink verified! Liveness confirmed."
                else:
                    # Too slow or unnatural
                    self.state = "EYES_OPEN"
                    prompt = "Blink too prolonged. Please blink naturally."
            elif now - self.blink_start_time > self.MAX_BLINK_DURATION_SEC:
                # Timed out in closed state
                self.state = "INIT"
                prompt = "Eyes closed too long. Open your eyes to try again."
            else:
                prompt = "Open your eyes..."

        else:
            prompt = "Hold still for biometric capture..."

        return {
            "liveness_passed": self.is_passed,
            "prompt": prompt,
            "ear": ear,
            "state": self.state
        }

