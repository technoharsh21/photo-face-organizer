"""
Auto-Capture Controller.

Pure per-frame decision logic for hands-free multi-angle face enrollment.
Given a stream of (pose_bucket, quality_stars) observations, it decides when
a distinct, stable, high-quality angle should be captured. No camera, no Qt.
"""

from domain.pose_classifier import POSE_BUCKETS


class AutoCaptureController:
    """Decides when to auto-capture each distinct pose bucket."""

    def __init__(self, stable_frames: int = 12, cooldown_frames: int = 24):
        self.stable_frames = stable_frames
        self.cooldown_frames = cooldown_frames
        self.filled: set[str] = set()
        self._current_bucket: str | None = None
        self._stable_count = 0
        self._cooldown = 0

    def observe(self, bucket: str | None, quality_stars: int) -> str | None:
        """Feed one frame. Returns a bucket name to capture now, else None."""
        if self._cooldown > 0:
            self._cooldown -= 1

        if bucket is None or bucket not in POSE_BUCKETS:
            self._current_bucket = None
            self._stable_count = 0
            return None

        if bucket == self._current_bucket:
            self._stable_count += 1
        else:
            self._current_bucket = bucket
            self._stable_count = 1

        if bucket in self.filled:
            return None
        if quality_stars < 4:
            return None
        if self._cooldown > 0:
            return None
        if self._stable_count < self.stable_frames:
            return None

        # Capture
        self.filled.add(bucket)
        self._stable_count = 0
        self._cooldown = self.cooldown_frames
        return bucket

    def is_complete(self) -> bool:
        return self.filled.issuperset(POSE_BUCKETS)

    def remaining(self) -> list[str]:
        return [b for b in POSE_BUCKETS if b not in self.filled]
