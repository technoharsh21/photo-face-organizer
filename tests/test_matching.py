"""
Tests for Face Matching Logic, Thresholds, and Compulsory Group Profiles.
"""

import numpy as np

from domain.matcher import FaceMatcher


class DummyFaceEngine:
    """Mock FaceEngine returning predefined distance scores for testing."""
    def __init__(self, predefined_distance: float):
        self.predefined_distance = predefined_distance

    def calculate_match_score(self, emb1, emb2):
        from domain.calibration import calibrate_match_score
        return calibrate_match_score(self.predefined_distance)


def test_matching_threshold_boundary():
    # Distance 0.6 maps to score 50.0 -> Match
    engine_50 = DummyFaceEngine(0.6)
    matcher = FaceMatcher(face_engine=engine_50, threshold=50.0)

    dummy_emb = np.zeros(128)
    profiles = [{"id": "p1", "name": "Harsh", "embeddings": [dummy_emb]}]

    res = matcher.match_face(dummy_emb, profiles)
    assert res.is_match is True
    assert res.matched_profile_name == "Harsh"
    assert res.match_score == 50.0

    # Distance 0.61 maps to score < 50.0 -> No Match
    engine_below = DummyFaceEngine(0.61)
    matcher_below = FaceMatcher(face_engine=engine_below, threshold=50.0)
    res_below = matcher_below.match_face(dummy_emb, profiles)
    assert res_below.is_match is False
    assert res_below.matched_profile_id is None


def test_matching_highest_score_wins():
    class MultiScoreEngine:
        def calculate_match_score(self, emb1, emb2):
            val = emb2[0]  # dummy encoding value
            return float(val)

    matcher = FaceMatcher(face_engine=MultiScoreEngine(), threshold=50.0)
    dummy_emb = np.zeros(128)

    profiles = [
        {"id": "p1", "name": "Rahul", "embeddings": [np.array([55.0])]},
        {"id": "p2", "name": "Harsh", "embeddings": [np.array([85.0])]},
        {"id": "p3", "name": "John", "embeddings": [np.array([70.0])]},
    ]

    res = matcher.match_face(dummy_emb, profiles)
    assert res.is_match is True
    assert res.matched_profile_name == "Harsh"
    assert res.match_score == 85.0


def test_compulsory_group_profile_matching():
    """Test Cases 5 & 6: Compulsory Group Profiles (e.g. Me & Friend)."""
    class MultiFaceEngine:
        def calculate_match_score(self, emb1, emb2):
            # emb1[0] indicates face identity: 1.0 for You, 2.0 for Friend
            if emb1[0] == emb2[0]:
                return 90.0
            return 10.0

    engine = MultiFaceEngine()
    matcher = FaceMatcher(face_engine=engine, threshold=50.0)

    p_you = {"id": "p_you", "name": "You", "embeddings": [np.array([1.0])]}
    p_friend = {"id": "p_friend", "name": "Friend", "embeddings": [np.array([2.0])]}
    p_group = {
        "id": "p_group",
        "name": "Me & Friend",
        "is_group_profile": True,
        "compulsory_profile_ids": ["p_you", "p_friend"],
        "embeddings": [],
    }

    profiles = [p_you, p_friend, p_group]

    # Scenario A: Both You (1.0) and Friend (2.0) detected in photo
    face_encs = [np.array([1.0]), np.array([2.0])]
    locs = [(0, 10, 10, 0), (20, 30, 30, 20)]

    matched_names, results = matcher.evaluate_photo_matches(face_encs, locs, profiles)
    assert "You" in matched_names
    assert "Friend" in matched_names
    assert "Me & Friend" in matched_names

    # Scenario B: Only You (1.0) present in photo, Friend absent -> Group profile should NOT match
    solo_encs = [np.array([1.0])]
    solo_locs = [(0, 10, 10, 0)]

    matched_names_solo, _ = matcher.evaluate_photo_matches(solo_encs, solo_locs, profiles)
    assert "You" in matched_names_solo
    assert "Friend" not in matched_names_solo
    assert "Me & Friend" not in matched_names_solo
