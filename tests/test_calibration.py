"""
Tests for Score Calibration Module.
"""

from domain.calibration import calibrate_match_score


def test_calibrate_match_score_exact_boundaries():
    # Distance 0.0 -> Score 100.0
    assert calibrate_match_score(0.0) == 100.0

    # Distance 0.6 -> Score 50.0 (Default threshold)
    assert calibrate_match_score(0.6) == 50.0

    # Distance 1.0 or greater -> Score 0.0
    assert calibrate_match_score(1.0) == 0.0
    assert calibrate_match_score(1.5) == 0.0

    # Distance 0.3 -> Score 75.0
    assert calibrate_match_score(0.3) == 75.0

    # Distance 0.8 -> Score 25.0
    assert calibrate_match_score(0.8) == 25.0


def test_calibrate_match_score_invalid_inputs():
    assert calibrate_match_score(None) == 0.0
    assert calibrate_match_score(-0.5) == 0.0
