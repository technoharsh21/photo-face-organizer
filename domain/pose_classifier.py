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
