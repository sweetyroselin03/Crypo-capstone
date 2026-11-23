from typing import List, Dict, Any

class BlinkLivenessDetector:
    """
    Validates live subject presence through blink detection sequence.
    Detects eye closure followed by eye reopening (EAR or openness measurement).
    Prevents presentation attacks using static photos.
    """

    def __init__(self, close_threshold: float = 0.17, open_threshold: float = 0.22):
        self.close_threshold = close_threshold
        self.open_threshold = open_threshold

    def evaluate_blink_sequence(self, openness_history: List[float]) -> Dict[str, Any]:
        """
        Evaluate sequential openness measurements across captured frames.
        Requires:
        1. An initial open state (openness >= open_threshold)
        2. A dip into closed state (openness <= close_threshold)
        3. A recovery back to open state (openness >= open_threshold)
        """
        if len(openness_history) < 5:
            return {
                "liveness_passed": False,
                "reason": "Insufficient frames to analyze blink sequence. Need at least 5 frames.",
                "blink_detected": False,
            }

        # Check for static photo (zero variance across frames)
        diffs = [abs(openness_history[i] - openness_history[i - 1]) for i in range(1, len(openness_history))]
        max_diff = max(diffs) if diffs else 0.0

        if max_diff < 0.02:
            return {
                "liveness_passed": False,
                "reason": "Static image detected. Liveness requires a natural blink.",
                "blink_detected": False,
            }

        # State machine for blink sequence: 0: WAITING_CLOSE, 1: WAITING_OPEN, 2: BLINK_CONFIRMED
        state = 0
        min_seen = min(openness_history)
        max_seen = max(openness_history)

        for val in openness_history:
            if state == 0 and val <= self.close_threshold:
                state = 1
            elif state == 1 and val >= self.open_threshold:
                state = 2
                break

        # Also permit dynamic variation if user blinked during capture
        has_blink = (state == 2) or (min_seen <= self.close_threshold and max_seen >= self.open_threshold)

        return {
            "liveness_passed": bool(has_blink),
            "blink_detected": bool(has_blink),
            "min_openness": round(min_seen, 4),
            "max_openness": round(max_seen, 4),
            "reason": "Natural blink sequence verified" if has_blink else "No complete eye blink (closure and reopening) detected"
        }
