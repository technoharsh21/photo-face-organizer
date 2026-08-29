"""
Unit tests for Solo Photo Scan & Move Mode Verification.
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from domain.insight_engine import InsightFaceEngine
from domain.solo_matcher import SoloFaceMatcher
from services.solo_scan_service import SoloScanService


@pytest.fixture
def mock_face_engine():
    return InsightFaceEngine(device_preference="CPU")


def test_solo_matcher_filtering(mock_face_engine):
    matcher = SoloFaceMatcher(face_engine=mock_face_engine, threshold=50.0)

    dummy_enc1 = np.ones(512, dtype=np.float64)
    dummy_enc2 = np.zeros(512, dtype=np.float64)

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
    fe = InsightFaceEngine(device_preference="CPU")
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


def test_exclusive_group_solo_matching(mock_face_engine):
    matcher = SoloFaceMatcher(face_engine=mock_face_engine, threshold=50.0)

    enc_harsh = np.ones(512, dtype=np.float64)
    enc_arya = np.ones(512, dtype=np.float64) * 0.9
    enc_stranger = np.zeros(512, dtype=np.float64)

    all_sys_profiles = [
        {"id": "p_harsh", "name": "Harsh", "is_group_profile": False, "embeddings": [enc_harsh.tolist()]},
        {"id": "p_arya", "name": "Arya", "is_group_profile": False, "embeddings": [enc_arya.tolist()]},
        {
            "id": "g_couple",
            "name": "Harsh & Arya",
            "is_group_profile": True,
            "compulsory_profile_ids": ["p_harsh", "p_arya"],
        },
    ]

    group_profiles_to_scan = [all_sys_profiles[2]]

    # Case 1: Photo has EXACTLY 2 faces (Harsh + Arya) -> Matched!
    names1, _ = matcher.evaluate_solo_photo_matches(
        face_encodings=[enc_harsh, enc_arya],
        face_locations=[(0, 50, 50, 0), (60, 110, 110, 60)],
        profiles=group_profiles_to_scan,
        all_system_profiles=all_sys_profiles,
    )
    assert "Harsh & Arya" in names1

    # Case 2: Photo has 3 faces (Harsh + Arya + Stranger) -> Rejected (Exact face count failed)
    names2, _ = matcher.evaluate_solo_photo_matches(
        face_encodings=[enc_harsh, enc_arya, enc_stranger],
        face_locations=[(0, 50, 50, 0), (60, 110, 110, 60), (120, 170, 170, 120)],
        profiles=group_profiles_to_scan,
        all_system_profiles=all_sys_profiles,
    )
    assert "Harsh & Arya" not in names2

    # Case 3: Photo has 2 faces (Harsh + Stranger) -> Rejected (Member Arya missing)
    names3, _ = matcher.evaluate_solo_photo_matches(
        face_encodings=[enc_harsh, enc_stranger],
        face_locations=[(0, 50, 50, 0), (60, 110, 110, 60)],
        profiles=group_profiles_to_scan,
        all_system_profiles=all_sys_profiles,
    )
    assert "Harsh & Arya" not in names3
