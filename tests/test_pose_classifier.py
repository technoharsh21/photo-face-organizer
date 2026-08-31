import numpy as np

from domain.pose_classifier import POSE_BUCKETS, classify_pose


def kps(le, re, nose, lm, rm):
    return np.array([le, re, nose, lm, rm], dtype=np.float32)


def test_buckets_constant():
    assert POSE_BUCKETS == ["frontal", "left", "right", "up", "smile"]


def test_frontal():
    k = kps([40, 50], [80, 50], [60, 70], [50, 90], [70, 90])
    assert classify_pose(k) == "frontal"


def test_turn_left():
    k = kps([40, 50], [80, 50], [46, 70], [50, 90], [70, 90])
    assert classify_pose(k) == "left"


def test_turn_right():
    k = kps([40, 50], [80, 50], [74, 70], [50, 90], [70, 90])
    assert classify_pose(k) == "right"


def test_tilt_up():
    k = kps([40, 50], [80, 50], [60, 55], [50, 90], [70, 90])
    assert classify_pose(k) == "up"


def test_smile():
    # smiling mouth corners spread wider than the inter-eye distance
    k = kps([40, 50], [80, 50], [60, 70], [33, 90], [87, 90])
    assert classify_pose(k) == "smile"


def test_degenerate_returns_none():
    k = kps([50, 50], [50, 50], [50, 50], [50, 50], [50, 50])
    assert classify_pose(k) is None


def test_wrong_shape_returns_none():
    assert classify_pose(np.zeros((3, 2), dtype=np.float32)) is None
    assert classify_pose(None) is None
