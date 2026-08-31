# Auto Live Face Enrollment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a hands-free "Auto Scan" mode to the live face scanner: the user holds their face to the camera, moves/turns their head, and the app automatically captures each distinct pose angle (front/left/right/up/smile) at good quality, then auto-enrolls the profile.

**Architecture:** A pure pose-classifier function maps SCRFD's 5 facial keypoints to a pose "bucket". The dialog runs a per-frame state machine in auto mode: classify pose → check the bucket is unfilled + quality ≥4 stars + pose held stable → capture. When all 5 buckets fill, it auto-enrolls via the existing `_finish_enrollment()` path. The manual 5-step flow stays untouched as a fallback toggle.

**Tech Stack:** Python 3.10+, PySide6 (QDialog/QTimer), OpenCV (cv2), NumPy, InsightFace SCRFD (keypoints), existing `ProfileService`/`FaceEngine`.

**Spec:** In-chat bounded design approved 2026-08-31 (this file is self-contained).

## Global Constraints

- No new ML models or pip dependencies — derive pose from existing SCRFD `kps` only
- Never break or alter the existing manual 5-step capture flow; auto mode is additive
- Reuse `ProfileService.assess_reference_quality(pil_img, bbox)` for quality gating (≥4 stars)
- Reuse `_finish_enrollment()` unchanged for the actual enrollment
- bbox tuple order is `(top, right, bottom, left)` everywhere (existing convention)
- `kps` is a NumPy array shape `(5, 2)`: rows = [left_eye, right_eye, nose, left_mouth, right_mouth], cols = [x, y] in image pixels
- Pure logic (pose classifier) lives in its own module and is unit-tested without a camera

---

## File Structure

- `domain/pose_classifier.py` (new) — pure function `classify_pose(kps) -> str` + constants. No Qt, no cv2 capture, no I/O. Fully unit-testable.
- `tests/test_pose_classifier.py` (new) — unit tests with synthetic keypoint arrays.
- `domain/insight_engine.py` (modify) — add `detect_faces_with_kps()` returning bbox + kps per face.
- `domain/face_engine.py` (modify) — add matching abstract/base method `detect_faces_with_kps()`.
- `ui/components/live_face_scanner_dialog.py` (modify) — auto-mode toggle, per-frame auto-capture state machine, dynamic overlay prompts, auto-finish.

---

### Task 1: Pose Classifier (pure logic)

**Files:**
- Create: `domain/pose_classifier.py`
- Test: `tests/test_pose_classifier.py`

**Interfaces:**
- Produces:
  - `POSE_BUCKETS: list[str] = ["frontal", "left", "right", "up", "smile"]`
  - `classify_pose(kps: "np.ndarray") -> str | None` — returns one of `POSE_BUCKETS`, or `None` if kps is invalid/ambiguous. Input is shape `(5,2)`: rows [left_eye, right_eye, nose, left_mouth, right_mouth].

**Pose rules (derived from 5 keypoints, mirrors `is_front_facing_face` math):**
- Let `le, re, nose, lm, rm = kps[0], kps[1], kps[2], kps[3], kps[4]`.
- `eye_dx = abs(re[0]-le[0])` (inter-eye pixel distance; scale reference). If `eye_dx < 2`, return `None` (degenerate).
- Horizontal nose offset: `dL = nose[0]-le[0]`, `dR = re[0]-nose[0]`. Ratio `yaw_r = (dR - dL) / eye_dx`.
  - `yaw_r > 0.35` → face turned so nose is closer to left eye → **"left"** (user turned head left; image already mirror-flipped in the dialog, but classifier is defined on raw kps geometry — the dialog passes the same flipped-frame kps it detects on, so "left" here means nose-nearer-left-eye).
  - `yaw_r < -0.35` → **"right"**.
- Vertical: eye midpoint `eye_y = (le[1]+re[1])/2`, mouth midpoint `mouth_y = (lm[1]+rm[1])/2`. `face_h = abs(mouth_y - eye_y)`. If `face_h < 2`, return `None`.
  - Nose relative vertical: `pitch_r = (nose[1] - eye_y) / face_h`. Frontal-neutral nose sits ~0.45–0.75 of eye→mouth span.
  - `pitch_r < 0.30` → chin/nose high relative to eyes → **"up"**.
- Expression (mouth openness/spread): `mouth_w = abs(rm[0]-lm[0])`. `smile_r = mouth_w / eye_dx`. `smile_r > 1.05` → **"smile"**.
- Priority when several could match: check in order **up → left → right → smile → frontal**. (Up and turns are more specific; frontal is the fallback when `abs(yaw_r) <= 0.35` and `pitch_r >= 0.30` and `smile_r <= 1.05`.)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pose_classifier.py
import numpy as np
from domain.pose_classifier import classify_pose, POSE_BUCKETS


def kps(le, re, nose, lm, rm):
    return np.array([le, re, nose, lm, rm], dtype=np.float32)


def test_buckets_constant():
    assert POSE_BUCKETS == ["frontal", "left", "right", "up", "smile"]


def test_frontal():
    # symmetric, nose centered, neutral mouth
    k = kps([40, 50], [80, 50], [60, 70], [50, 90], [70, 90])
    assert classify_pose(k) == "frontal"


def test_turn_left():
    # nose shifted toward left eye (dR >> dL)
    k = kps([40, 50], [80, 50], [46, 70], [50, 90], [70, 90])
    assert classify_pose(k) == "left"


def test_turn_right():
    # nose shifted toward right eye (dL >> dR)
    k = kps([40, 50], [80, 50], [74, 70], [50, 90], [70, 90])
    assert classify_pose(k) == "right"


def test_tilt_up():
    # nose vertically close to eye line (chin up)
    k = kps([40, 50], [80, 50], [60, 55], [50, 90], [70, 90])
    assert classify_pose(k) == "up"


def test_smile():
    # wide mouth relative to eye distance
    k = kps([40, 50], [80, 50], [60, 70], [40, 90], [80, 90])
    assert classify_pose(k) == "smile"


def test_degenerate_returns_none():
    k = kps([50, 50], [50, 50], [50, 50], [50, 50], [50, 50])
    assert classify_pose(k) is None


def test_wrong_shape_returns_none():
    assert classify_pose(np.zeros((3, 2), dtype=np.float32)) is None
    assert classify_pose(None) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -m pytest tests/test_pose_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.pose_classifier'`

- [ ] **Step 3: Implement `domain/pose_classifier.py`**

```python
"""
Pose Classifier.

Pure geometric classification of head pose from SCRFD's 5 facial keypoints.
No camera, no Qt, no I/O — unit-testable in isolation. Used by the live face
scanner's auto-capture mode to bucket frames into distinct enrollment angles.
"""

from typing import Any

import numpy as np

POSE_BUCKETS: list[str] = ["frontal", "left", "right", "up", "smile"]

_YAW_THRESH = 0.35
_PITCH_UP_THRESH = 0.30
_SMILE_THRESH = 1.05


def classify_pose(kps: Any) -> str | None:
    """
    Classify head pose from 5 keypoints (left_eye, right_eye, nose, left_mouth,
    right_mouth), each (x, y). Returns a bucket in POSE_BUCKETS or None if the
    keypoints are missing, wrong-shaped, or degenerate.
    """
    if kps is None:
        return None
    arr = np.asarray(kps, dtype=np.float32)
    if arr.shape != (5, 2):
        return None

    le, re, nose, lm, rm = arr[0], arr[1], arr[2], arr[3], arr[4]

    eye_dx = abs(float(re[0] - le[0]))
    if eye_dx < 2.0:
        return None

    d_left = float(nose[0] - le[0])
    d_right = float(re[0] - nose[0])
    yaw_r = (d_right - d_left) / eye_dx

    eye_y = (float(le[1]) + float(re[1])) / 2.0
    mouth_y = (float(lm[1]) + float(rm[1])) / 2.0
    face_h = abs(mouth_y - eye_y)
    if face_h < 2.0:
        return None
    pitch_r = (float(nose[1]) - eye_y) / face_h

    mouth_w = abs(float(rm[0] - lm[0]))
    smile_r = mouth_w / eye_dx

    # Priority: up -> left -> right -> smile -> frontal
    if pitch_r < _PITCH_UP_THRESH:
        return "up"
    if yaw_r > _YAW_THRESH:
        return "left"
    if yaw_r < -_YAW_THRESH:
        return "right"
    if smile_r > _SMILE_THRESH:
        return "smile"
    return "frontal"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -m pytest tests/test_pose_classifier.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add domain/pose_classifier.py tests/test_pose_classifier.py
git commit -m "feat: add pure pose classifier from SCRFD keypoints for auto face capture"
```

---

### Task 2: Engine helper `detect_faces_with_kps`

**Files:**
- Modify: `domain/insight_engine.py` (add method to `InsightFaceEngine`, near `detect_faces` ~line 516)
- Modify: `domain/face_engine.py` (add non-abstract default method to `FaceEngine` base, near `detect_and_embed_faces` ~line 46)
- Test: `tests/test_detect_faces_with_kps.py`

**Interfaces:**
- Consumes: existing `self._run_inference(app, img_bgr, det_thresh)`, `self._preprocess_bgr_image`, `self._to_numpy_bgr`, `self.is_valid_face_geometry`.
- Produces on `InsightFaceEngine`:
  - `detect_faces_with_kps(self, image, det_thresh: float | None = None) -> list[tuple[tuple[int,int,int,int], "np.ndarray | None"]]`
  - Each element: `((top, right, bottom, left), kps)` where `kps` is `np.ndarray (5,2)` or `None`.
- Produces on `FaceEngine` base: a default implementation that calls `self.detect_faces(...)` and returns `[(loc, None), ...]` so non-Insight engines still satisfy the interface.

- [ ] **Step 1: Write failing test (base-class fallback, no camera/model needed)**

```python
# tests/test_detect_faces_with_kps.py
from domain.face_engine import FaceEngine


class _StubEngine(FaceEngine):
    def detect_faces(self, image, model="hog", det_thresh=None):
        return [(10, 90, 100, 20)]

    def extract_faces(self, image, face_locations=None):
        return []

    def create_embeddings(self, image, face_locations=None):
        return []

    def compare_embeddings(self, e1, e2):
        return 0.0

    def calculate_match_score(self, e1, e2):
        return 0.0

    def set_device_preference(self, preference):
        return "CPU"

    def get_device_info(self):
        return {}


def test_base_detect_faces_with_kps_fallback():
    eng = _StubEngine()
    result = eng.detect_faces_with_kps(None)
    assert result == [((10, 90, 100, 20), None)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -m pytest tests/test_detect_faces_with_kps.py -v`
Expected: FAIL with `AttributeError: 'FaceEngine' object has no attribute 'detect_faces_with_kps'` (or the stub cannot be constructed because the method is abstract — it is not; we add a concrete default).

- [ ] **Step 3: Add default method to `FaceEngine` base**

In `domain/face_engine.py`, inside class `FaceEngine`, after the `detect_and_embed_faces` method (around line 56), add:

```python
    def detect_faces_with_kps(
        self, image: Any, det_thresh: float | None = None
    ) -> list[tuple[tuple[int, int, int, int], "np.ndarray | None"]]:
        """
        Detect faces returning (bbox, keypoints) pairs.
        Default implementation returns None keypoints; engines that expose
        landmark keypoints (e.g. InsightFace SCRFD) override this.
        bbox order: (top, right, bottom, left).
        """
        return [(loc, None) for loc in self.detect_faces(image, det_thresh=det_thresh)]
```

- [ ] **Step 4: Override in `InsightFaceEngine`**

In `domain/insight_engine.py`, add this method to `InsightFaceEngine` right after `detect_faces` (after ~line 573):

```python
    def detect_faces_with_kps(
        self, image: Any, det_thresh: float | None = None
    ) -> list[tuple[tuple[int, int, int, int], "np.ndarray | None"]]:
        """
        Detect faces returning (bbox, 5-point keypoints) pairs.
        bbox order: (top, right, bottom, left). kps is np.ndarray (5,2) or None.
        """
        self._ensure_initialized()
        if self.app is None:
            return []

        img_bgr = self._preprocess_bgr_image(self._to_numpy_bgr(image))
        results: list[tuple[tuple[int, int, int, int], "np.ndarray | None"]] = []
        try:
            faces = self._run_inference(self.app, img_bgr, det_thresh=det_thresh)
            for face in faces:
                bbox = face.bbox.astype(int)  # [left, top, right, bottom]
                kps = getattr(face, "kps", None)
                if not self.is_valid_face_geometry(bbox, kps):
                    continue
                left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                kps_arr = None
                if kps is not None:
                    import numpy as np
                    kps_arr = np.asarray(kps, dtype=np.float32)
                    if kps_arr.shape != (5, 2):
                        kps_arr = None
                results.append(((top, right, bottom, left), kps_arr))
        except Exception as e:
            logger.warning(f"detect_faces_with_kps exception on {self.active_device}: {e}")
            return []
        return results
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -m pytest tests/test_detect_faces_with_kps.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add domain/face_engine.py domain/insight_engine.py tests/test_detect_faces_with_kps.py
git commit -m "feat: add detect_faces_with_kps engine helper exposing SCRFD keypoints"
```

---

### Task 3: Auto-capture state machine (pure, no Qt)

**Files:**
- Create: `domain/auto_capture_controller.py`
- Test: `tests/test_auto_capture_controller.py`

**Rationale:** Keep the capture decision logic testable without a camera or Qt. The dialog feeds it per-frame observations; it decides when a bucket should be captured.

**Interfaces:**
- Consumes: `POSE_BUCKETS` from `domain.pose_classifier`.
- Produces class `AutoCaptureController`:
  - `__init__(self, stable_frames: int = 12, cooldown_frames: int = 24)`
  - `filled: set[str]` — buckets already captured.
  - `observe(self, bucket: str | None, quality_stars: int) -> str | None` — call once per frame. Returns a bucket name when THAT frame should be captured now, else `None`. Rules: bucket must be non-None, not already in `filled`, `quality_stars >= 4`, the same bucket observed for `stable_frames` consecutive frames, and at least `cooldown_frames` since the last capture. On a capture it adds the bucket to `filled`, resets the stability counter, and starts the cooldown.
  - `is_complete(self) -> bool` — `filled` covers all `POSE_BUCKETS`.
  - `remaining(self) -> list[str]` — buckets still empty, in `POSE_BUCKETS` order.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auto_capture_controller.py
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
    c = AutoCaptureController(stable_frames=3, cooldown_frames=0)
    c.observe("frontal", 5)
    c.observe("left", 5)          # changed -> resets
    assert c.observe("frontal", 5) is None   # only 2 frontal in a row since reset
    assert c.observe("frontal", 5) == "frontal"


def test_cooldown_blocks_immediate_second_capture():
    c = AutoCaptureController(stable_frames=1, cooldown_frames=3)
    assert c.observe("frontal", 5) == "frontal"
    # different bucket, stable=1, but cooldown active
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -m pytest tests/test_auto_capture_controller.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.auto_capture_controller'`

- [ ] **Step 3: Implement `domain/auto_capture_controller.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -m pytest tests/test_auto_capture_controller.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add domain/auto_capture_controller.py tests/test_auto_capture_controller.py
git commit -m "feat: add auto-capture controller for hands-free multi-angle enrollment"
```

---

### Task 4: Wire auto mode into the live scanner dialog

**Files:**
- Modify: `ui/components/live_face_scanner_dialog.py`

**Interfaces:**
- Consumes: `classify_pose`, `POSE_BUCKETS` (`domain.pose_classifier`); `AutoCaptureController` (`domain.auto_capture_controller`); `self.face_engine.detect_faces_with_kps(...)`; `ProfileService.assess_reference_quality(pil_img, bbox)`; existing `self._capture_angle`, `self._finish_enrollment`, `self.angle_widgets`, `self.captured_images`, `ENROLLMENT_STEPS`.
- Note: `ENROLLMENT_STEPS` ids are `frontal, left, right, tilt_up, smile`. Map pose buckets to step indices: `frontal→0, left→1, right→2, up→3, smile→4`. The pose bucket `"up"` maps to step id `"tilt_up"`.

**Behavior added:**
- New instance state in `__init__`: `self.auto_mode = False`, `self.auto_controller: AutoCaptureController | None = None`, `self._bucket_to_step = {"frontal":0,"left":1,"right":2,"up":3,"smile":4}`.
- New toggle button `btn_auto_scan` ("⚡ Auto Scan: OFF") in the bottom bar. Clicking flips `self.auto_mode`, updates label to ON/OFF, and (on ON) creates a fresh `AutoCaptureController()` and disables the manual `btn_capture`/`btn_auto` countdown buttons; (on OFF) re-enables them.
- In `_update_camera_frame`, when `self.auto_mode` and a face is present: get `(bbox, kps)` via `detect_faces_with_kps`, classify pose, assess quality stars, feed `self.auto_controller.observe(bucket, stars)`. If it returns a bucket, set `self.current_step_idx = self._bucket_to_step[bucket]` and call `self._capture_angle()` (reuses existing capture+thumbnail+progress logic). Then, if `self.auto_controller.is_complete()`, stop auto mode and call `self._auto_finish()`.
- Overlay prompt: draw the next remaining bucket instruction on the cv2 frame (e.g. "Turn LEFT", "Look UP", "SMILE", "Look STRAIGHT") using `self.auto_controller.remaining()[0]`.
- `_auto_finish`: show a 1.5s single-shot QTimer then call the existing `self._finish_enrollment()`.

- [ ] **Step 1: Add imports and init state**

At the top of `ui/components/live_face_scanner_dialog.py`, after `from services.profile_service import ProfileService`, add:

```python
from domain.pose_classifier import classify_pose, POSE_BUCKETS
from domain.auto_capture_controller import AutoCaptureController
```

In `__init__`, after `self.created_profile_id: str | None = None` (line ~110), add:

```python
        # Auto-capture (hands-free) mode state
        self.auto_mode = False
        self.auto_controller: AutoCaptureController | None = None
        self._bucket_to_step = {"frontal": 0, "left": 1, "right": 2, "up": 3, "smile": 4}
```

- [ ] **Step 2: Add the Auto Scan toggle button**

In `_setup_ui`, in the `bottom_bar` section, immediately after the `self.btn_auto` block (after line ~325, before `self.btn_finish`), add:

```python
        self.btn_auto_scan = QPushButton("⚡ Auto Scan: OFF")
        self.btn_auto_scan.setProperty("class", "SecondaryButton")
        self.btn_auto_scan.setFixedHeight(36)
        self.btn_auto_scan.setCursor(Qt.PointingHandCursor)
        self.btn_auto_scan.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_auto_scan.clicked.connect(self._toggle_auto_mode)
        bottom_bar.addWidget(self.btn_auto_scan)
```

- [ ] **Step 3: Add `_toggle_auto_mode`**

Add this method to the class (near `_start_countdown`):

```python
    def _toggle_auto_mode(self):
        """Enable/disable hands-free auto-capture mode."""
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            self.auto_controller = AutoCaptureController()
            # pre-mark already-captured buckets so auto mode doesn't redo them
            step_to_bucket = {v: k for k, v in self._bucket_to_step.items()}
            for idx in self.captured_images:
                b = step_to_bucket.get(idx)
                if b:
                    self.auto_controller.filled.add(b)
            self.btn_auto_scan.setText("⚡ Auto Scan: ON")
            self.btn_auto_scan.setStyleSheet(
                "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
                "QPushButton:hover { background-color: #059669; }"
            )
            self.btn_capture.setEnabled(False)
            self.btn_auto.setEnabled(False)
        else:
            self.auto_controller = None
            self.btn_auto_scan.setText("⚡ Auto Scan: OFF")
            self.btn_auto_scan.setStyleSheet(
                "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
                "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
            )
            self.btn_capture.setEnabled(True)
            self.btn_auto.setEnabled(True)
```

- [ ] **Step 4: Add per-frame auto logic + overlay in `_update_camera_frame`**

In `_update_camera_frame`, replace the existing face-detection block:

```python
        pil_img = Image.fromarray(self.current_frame_rgb)
        try:
            locs = self.face_engine.detect_faces(pil_img)
            face_detected = bool(locs)
            self.last_detected_bbox = locs[0] if locs else None
        except Exception:
            face_detected = False
            self.last_detected_bbox = None
```

with:

```python
        pil_img = Image.fromarray(self.current_frame_rgb)
        frame_kps = None
        try:
            det = self.face_engine.detect_faces_with_kps(pil_img)
            face_detected = bool(det)
            if det:
                self.last_detected_bbox, frame_kps = det[0]
            else:
                self.last_detected_bbox = None
        except Exception:
            face_detected = False
            self.last_detected_bbox = None

        # Hands-free auto-capture decision
        if self.auto_mode and self.auto_controller is not None and self.last_detected_bbox is not None:
            bucket = classify_pose(frame_kps) if frame_kps is not None else None
            try:
                q = ProfileService.assess_reference_quality(pil_img, list(self.last_detected_bbox))
                stars = int(q.get("stars", 0))
            except Exception:
                stars = 0
            to_capture = self.auto_controller.observe(bucket, stars)
            if to_capture is not None:
                self.current_step_idx = self._bucket_to_step[to_capture]
                self._capture_angle()
                if self.auto_controller.is_complete():
                    self.auto_mode = False
                    self._auto_finish()
```

Then, after the existing countdown-overlay block (after line ~416, before `cv2.addWeighted(...)`), add the auto-mode prompt overlay:

```python
        if self.auto_mode and self.auto_controller is not None:
            remaining = self.auto_controller.remaining()
            prompt_map = {
                "frontal": "Look STRAIGHT",
                "left": "Turn LEFT",
                "right": "Turn RIGHT",
                "up": "Look UP",
                "smile": "SMILE",
            }
            prompt = prompt_map.get(remaining[0], "Hold still") if remaining else "All angles captured!"
            cv2.putText(
                overlay, prompt, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                (0, 230, 255), 3, cv2.LINE_AA,
            )
```

- [ ] **Step 5: Add `_auto_finish`**

Add this method to the class:

```python
    def _auto_finish(self):
        """After all buckets captured, briefly show success then enroll."""
        self.btn_auto_scan.setText("✅ All angles captured!")
        QTimer.singleShot(1500, self._finish_enrollment)
```

- [ ] **Step 6: Verify the dialog imports and compiles**

Run:
```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && python3 -m py_compile ui/components/live_face_scanner_dialog.py && echo "OK"
```
Expected: `OK`

Then verify wiring with an offscreen smoke test (no real camera; construct is skipped, just import path + classifier round-trip):
```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python -c "
from domain.auto_capture_controller import AutoCaptureController
from domain.pose_classifier import classify_pose, POSE_BUCKETS
c = AutoCaptureController(stable_frames=1, cooldown_frames=0)
import numpy as np
k = np.array([[40,50],[80,50],[60,70],[50,90],[70,90]], dtype=np.float32)
print('bucket=', classify_pose(k), 'captured=', c.observe(classify_pose(k), 5))
print('OK')
"
```
Expected: prints `bucket= frontal captured= frontal` then `OK`.

- [ ] **Step 7: Commit**

```bash
git add ui/components/live_face_scanner_dialog.py
git commit -m "feat: hands-free auto-capture mode in live face scanner (pose-bucketed multi-angle enrollment)"
```

---

### Task 5: Manual verification checklist (camera)

**Files:** none (manual QA).

This task has no automated test — it documents the human smoke test the implementer runs before declaring done. It is a real gate: the reviewer confirms the implementer reported these results.

- [ ] **Step 1: Launch app and open the scanner**

```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && venv/bin/python app.py
```
Navigate: People Profiles → Create Profile / Add Reference → open the 🎥 Live Face Scanner (via the live scan button).

- [ ] **Step 2: Verify auto flow**

Enter a name. Click "⚡ Auto Scan: OFF" → turns ON (green), manual capture buttons disable. Hold face to camera; follow on-screen prompts (Look STRAIGHT → Turn LEFT → Turn RIGHT → Look UP → SMILE). Confirm each gallery slot fills automatically as you hit that pose, without pressing any button.

- [ ] **Step 3: Verify auto-finish + fallback**

After all 5 slots fill, confirm the button shows "✅ All angles captured!" and the enrollment completes/closes ~1.5s later, creating the profile with reference photos. Re-open, verify toggling Auto OFF restores the manual capture buttons and the manual 5-step flow still works.

- [ ] **Step 4: Report results** in the task report (pass/fail per step, any glitches).

---

## Self-Review

**Spec coverage:**
- New Auto toggle alongside manual flow → Task 4 (btn_auto_scan, toggle). ✓
- Continuous pose tracking from kps → Task 1 (classify_pose) + Task 2 (detect_faces_with_kps). ✓
- Quality gate ≥4 stars → Task 3 (observe requires stars≥4) + Task 4 (assess_reference_quality). ✓
- Stability + cooldown → Task 3 (stable_frames, cooldown_frames). ✓
- 5 pose buckets + auto-finish → Task 3 (is_complete) + Task 4 (_auto_finish). ✓
- Live guidance overlay → Task 4 (prompt overlay). ✓
- Reuse enrollment path unchanged → Task 4 reuses `_capture_angle` + `_finish_enrollment`. ✓
- Manual flow untouched → auto logic is gated on `self.auto_mode`; manual methods unchanged. ✓

**Placeholder scan:** none — every code step has full code.

**Type consistency:** `POSE_BUCKETS` list identical in Tasks 1/3/4. `classify_pose(kps)->str|None` consistent. `detect_faces_with_kps` returns `list[((top,right,bottom,left), kps|None)]` consistent between Task 2 producer and Task 4 consumer. `_bucket_to_step` keys exactly match `POSE_BUCKETS`. `observe(bucket, stars)->bucket|None` consistent Task 3↔4.

**Note on "up" bucket:** pose bucket `"up"` maps to `ENROLLMENT_STEPS[3]` whose id is `"tilt_up"` — mapping handled via `_bucket_to_step`, not by id-string matching, so no mismatch.
