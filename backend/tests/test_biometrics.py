import pytest
import numpy as np
from app.biometric.matcher import BiometricMatcher
from app.biometric.liveness import BlinkLivenessDetector

def test_cosine_similarity():
    """Verify cosine similarity calculation."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    sim_ident = BiometricMatcher.cosine_similarity(np.array(v1), np.array(v2))
    assert pytest.approx(sim_ident, 0.001) == 1.0

    sim_ortho = BiometricMatcher.cosine_similarity(np.array(v1), np.array(v3))
    assert pytest.approx(sim_ortho, 0.001) == 0.0


def test_enrollment_template_aggregation():
    """Test aggregation of multiple frame vectors."""
    vectors = [
        [0.5, 0.5, 0.5, 0.5],
        [0.6, 0.4, 0.5, 0.5],
        [0.4, 0.6, 0.5, 0.5],
    ]
    master = BiometricMatcher.aggregate_enrollment_template(vectors)
    assert len(master) == 4
    # Master vector should be L2 normalized (norm == 1.0)
    norm = np.linalg.norm(master)
    assert pytest.approx(norm, 0.001) == 1.0


def test_blink_liveness_detection():
    """Test that valid blink passes and static photo fails."""
    detector = BlinkLivenessDetector(close_threshold=0.17, open_threshold=0.22)

    # Valid blink sequence: open -> closed (<0.17) -> open (>0.22)
    valid_seq = [0.24, 0.23, 0.15, 0.12, 0.21, 0.24]
    res_valid = detector.evaluate_blink_sequence(valid_seq)
    assert res_valid["liveness_passed"] is True

    # Static photo: virtually constant openness
    static_seq = [0.24, 0.241, 0.24, 0.241, 0.24, 0.24]
    res_static = detector.evaluate_blink_sequence(static_seq)
    assert res_static["liveness_passed"] is False
    assert "Static image" in res_static["reason"]
