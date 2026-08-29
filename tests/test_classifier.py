"""
Unit tests for Profile Classifier & Continuous Self-Learning Service.
"""

import numpy as np
from services.classifier_service import ProfileClassifierService


def test_classifier_training_and_margin_evaluation():
    service = ProfileClassifierService()

    # Create two distinct clusters of 512-d embeddings
    vec_a1 = np.ones(512, dtype=np.float64) * 0.9
    vec_a2 = np.ones(512, dtype=np.float64) * 0.85
    vec_b1 = np.ones(512, dtype=np.float64) * -0.9
    vec_b2 = np.ones(512, dtype=np.float64) * -0.85

    profiles = [
        {"id": "p_a", "name": "Person A", "embeddings": [vec_a1.tolist(), vec_a2.tolist()]},
        {"id": "p_b", "name": "Person B", "embeddings": [vec_b1.tolist(), vec_b2.tolist()]},
    ]

    # Test training
    trained = service.train_classifier(profiles)
    assert trained is True

    # Test evaluating discriminative margin for Person A candidate
    cand_a = np.ones(512, dtype=np.float64) * 0.88
    base_score = 75.0
    adjusted_score = service.evaluate_discriminative_margin(cand_a, "p_a", base_score)
    assert adjusted_score >= base_score


def test_auto_learn_bundled_centroid():
    service = ProfileClassifierService()
    v1 = np.array([1.0] * 512)
    v2 = np.array([0.5] * 512)

    centroid = service.auto_learn_bundled_centroid([v1, v2])
    assert centroid is not None
    assert len(centroid) == 512
    # Verify unit length normalization
    norm = np.linalg.norm(centroid)
    assert abs(norm - 1.0) < 1e-4
