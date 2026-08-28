"""
Unit tests for Solo Photo Scan & Move Mode Verification.
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from domain.face_engine import FaceRecognitionEngine
from domain.solo_matcher import SoloFaceMatcher
from services.solo_scan_service import SoloScanService


@pytest.fixture
def mock_face_engine():
    return FaceRecognitionEngine(device_preference="CPU")


def test_solo_matcher_filtering(mock_face_engine):
    matcher = SoloFaceMatcher(face_engine=mock_face_engine, threshold=50.0)

    dummy_enc1 = np.ones(128, dtype=np.float64)
    dummy_enc2 = np.zeros(128, dtype=np.float64)

    profiles = [
        {"id": "p1", "name": "Harsh", "embeddings": [dummy_enc1.tolist()]},
    ]

    # Test 1: Single Face Photo -> Matched
    names_solo, res_solo = matcher.evaluate_solo_photo_matches(
        face_encodings=[dummy_enc1],
        face_locations=[(0, 50, 50, 0)],
        profiles=profiles,
    )
    assert "Harsh" in names_solo
    assert len(res_solo) == 1

    # Test 2: Group Photo (2 faces) -> Rejected from solo matching
    names_group, res_group = matcher.evaluate_solo_photo_matches(
        face_encodings=[dummy_enc1, dummy_enc2],
        face_locations=[(0, 50, 50, 0), (60, 110, 110, 60)],
        profiles=profiles,
    )
    assert len(names_group) == 0
    assert len(res_group) == 2


def test_solo_scan_service_verification(tmp_path):
    src_dir = tmp_path / "sources"
    tgt_dir = tmp_path / "target"
    src_dir.mkdir()
    tgt_dir.mkdir()

    # Create dummy source and copied target
    src_file = src_dir / "photo1.jpg"
    tgt_file = tgt_dir / "photo1.jpg"

    content = b"fake photo image bytes content 12345"
    src_file.write_bytes(content)
    tgt_file.write_bytes(content)

    from config import Config
    from services.history_service import HistoryService
    from services.output_service import OutputService
    from domain.duplicate_detector import DuplicateDetector
    from services.profile_service import ProfileService
    from services.unknown_face_service import UnknownFaceService

    cfg = Config(app_data_dir=tmp_path / "appdata")
    fe = FaceRecognitionEngine(device_preference="CPU")
    dd = DuplicateDetector(cfg.duplicate_index_file)
    ops = OutputService(dd)
    ps = ProfileService(cfg, fe)
    ufs = UnknownFaceService(cfg, ps)
    hs = HistoryService(cfg)

    service = SoloScanService(cfg, fe, ops, ufs, hs, ps)

    copied_pairs = [(str(src_file), str(tgt_file))]

    # Verify 100% match
    verified, count, verified_sources = service.verify_copied_photos(copied_pairs)
    assert verified is True
    assert count == 1
    assert str(src_file) in verified_sources

    # Test safe deletion
    del_count, err_count = service.delete_verified_sources(verified_sources)
    assert del_count == 1
    assert err_count == 0
    assert not src_file.exists()
    assert tgt_file.exists()
