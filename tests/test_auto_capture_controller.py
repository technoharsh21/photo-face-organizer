from domain.auto_capture_controller import AutoCaptureController
from domain.pose_classifier import POSE_BUCKETS


def test_captures_after_stable_frames():
    c = AutoCaptureController(stable_frames=3, cooldown_frames=2)
    assert c.observe("frontal", 5) is None   # 1
    assert c.observe("frontal", 5) is None   # 2
    assert c.observe("frontal", 5) == "frontal"  # 3rd stable frame -> capture
    assert "frontal" in c.filled


def test_low_quality_never_captures():
    c = AutoCaptureController(stable_frames=2, cooldown_frames=0)
    assert c.observe("frontal", 3) is None
    assert c.observe("frontal", 3) is None
    assert c.observe("frontal", 3) is None
    assert "frontal" not in c.filled


def test_pose_change_resets_stability():
    c = AutoCaptureController(stable_frames=2, cooldown_frames=0)
    c.observe("frontal", 5)       # frontal stable=1
    c.observe("left", 5)          # pose changed -> resets frontal streak
    assert c.observe("frontal", 5) is None       # frontal stable=1 again (reset worked)
    assert c.observe("frontal", 5) == "frontal"  # frontal stable=2 -> capture


def test_cooldown_blocks_immediate_second_capture():
    c = AutoCaptureController(stable_frames=1, cooldown_frames=3)
    assert c.observe("frontal", 5) == "frontal"
    assert c.observe("left", 5) is None
    assert c.observe("left", 5) is None
    assert c.observe("left", 5) == "left"


def test_none_bucket_ignored():
    c = AutoCaptureController(stable_frames=1, cooldown_frames=0)
    assert c.observe(None, 5) is None


def test_already_filled_not_recaptured():
    c = AutoCaptureController(stable_frames=1, cooldown_frames=0)
    assert c.observe("frontal", 5) == "frontal"
    assert c.observe("frontal", 5) is None


def test_completion_and_remaining():
    c = AutoCaptureController(stable_frames=1, cooldown_frames=0)
    for b in POSE_BUCKETS:
        c.observe(b, 5)
    assert c.is_complete()
    assert c.remaining() == []
