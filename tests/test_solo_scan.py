"""
Unit tests for Solo Photo Scan & Move Mode Verification.
"""

import tempfile
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from domain.insight_engine import InsightFaceEngine
from domain.solo_matcher import SoloFaceMatcher
from services.solo_scan_service import SoloScanService
from services.scan_service import ScanService
from domain.solo_worker import SoloScanWorker


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


def test_photobomber_and_geometry_features(mock_face_engine):
    matcher = SoloFaceMatcher(face_engine=mock_face_engine, threshold=50.0)

    enc_harsh = np.ones(512, dtype=np.float64)
    enc_photobomber = np.zeros(512, dtype=np.float64)
    profiles = [{"id": "p_harsh", "name": "Harsh", "is_group_profile": False, "embeddings": [enc_harsh.tolist()]}]

    # Large dominant foreground face (300x300 = 90,000 px) + tiny background photobomber (30x30 = 900 px)
    loc_dominant = (50, 350, 350, 50)
    loc_photobomber = (10, 40, 40, 10)

    # 1. Strict Mode (Default): Photo with 2 faces is rejected
    names_strict, _ = matcher.evaluate_solo_photo_matches(
        face_encodings=[enc_harsh, enc_photobomber],
        face_locations=[loc_dominant, loc_photobomber],
        profiles=profiles,
        allow_distant_photobombers=False,
    )
    assert len(names_strict) == 0

    # 2. Dominant Subject Photobomber Mode: Main subject dominates >= 90% face area -> Accepted!
    names_dominant, _ = matcher.evaluate_solo_photo_matches(
        face_encodings=[enc_harsh, enc_photobomber],
        face_locations=[loc_dominant, loc_photobomber],
        profiles=profiles,
        allow_distant_photobombers=True,
    )
    assert "Harsh" in names_dominant

    # 3. Geometry Validation: Normal face vs tiny sliver/invalid aspect ratio
    assert mock_face_engine.is_valid_face_geometry([10, 10, 100, 100]) is True
    assert mock_face_engine.is_valid_face_geometry([0, 0, 4, 4]) is False  # too small (<=8px)
    assert mock_face_engine.is_valid_face_geometry([0, 0, 200, 5]) is False  # extreme aspect ratio

    # 4. Sharpness calculation
    dummy_img = np.ones((50, 50, 3), dtype=np.uint8) * 128
    score = mock_face_engine.calculate_face_sharpness(dummy_img)
    assert isinstance(score, float)


@pytest.mark.parametrize("service_type", [ScanService, SoloScanService])
def test_move_mode_never_removes_unverified_or_changed_files(tmp_path, service_type):
    service = service_type.__new__(service_type)
    service._verified_copies = {}
    src, dst = tmp_path / "source.jpg", tmp_path / "target.jpg"
    src.write_bytes(b"AAAA")
    dst.write_bytes(b"BBBB")
    assert service.verify_copied_photos([(str(src), str(dst))]) == (False, 0, [])
    assert service.delete_verified_sources([str(src)]) == (0, 1)
    assert src.read_bytes() == b"AAAA"

    dst.write_bytes(b"AAAA")
    verified, count, sources = service.verify_copied_photos([(str(src), str(dst))])
    assert (verified, count) == (True, 1)
    dst.write_bytes(b"CCCC")
    assert service.delete_verified_sources(sources) == (0, 1)
    assert src.exists()

    dst.write_bytes(b"AAAA")
    _, _, sources = service.verify_copied_photos([(str(src), str(dst))])
    src.write_bytes(b"DDDD")
    assert service.delete_verified_sources(sources) == (0, 1)
    assert src.read_bytes() == b"DDDD"

    src.write_bytes(b"AAAA")
    _, _, sources = service.verify_copied_photos([(str(src), str(dst))])
    with patch("domain.file_utils.send_to_trash", return_value=False):
        assert service.delete_verified_sources(sources) == (0, 1)
    assert src.exists()


def test_solo_recovery_keeps_solo_worker_and_settings(tmp_path):
    from config import Config

    config = Config(app_data_dir=tmp_path / "data")
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "one.jpg").write_bytes(b"already processed")
    (photos / "two.jpg").write_bytes(b"still pending")
    scan_id = "solo-recovery"
    scan_dir = config.scans_dir / scan_id
    scan_dir.mkdir(parents=True)
    meta = {"scan_id": scan_id, "scan_type": "Solo Scan", "sources": [str(photos)],
            "profile_ids": ["person"], "output_dir": str(tmp_path / "output"), "recursive": False,
            "threshold": 81.0, "operation_mode": "move", "performance_mode": "Eco",
            "folder_organization": "year_only"}
    checkpoint = {"status": "Running", "current_index": 1, "processed_count": 1,
                  "processed_files": [str(photos / "one.jpg")]}
    (scan_dir / "scan.json").write_text(json.dumps(meta))
    (scan_dir / "checkpoint.json").write_text(json.dumps(checkpoint))
    profiles = MagicMock()
    profiles.get_profile.return_value = {"id": "person", "name": "Person", "embeddings": []}
    profiles.list_profiles.return_value = [profiles.get_profile.return_value]
    services = [MagicMock() for _ in range(4)]
    solo = SoloScanService(config, services[0], services[1], services[2], services[3], profiles)
    regular = ScanService(config, services[0], services[1], services[2], services[3], profiles)

    assert regular.resume_scan(scan_id) is None
    result = solo.resume_scan(scan_id)
    assert result is not None
    worker, restored = result
    assert isinstance(worker, SoloScanWorker)
    assert worker.threshold == 81.0 and worker.operation_mode == "move"
    assert worker.folder_organization == "year_only" and worker.performance_mode == "Eco"
    assert worker.start_index == 0 and worker.processed_count == 1
    assert str(photos / "one.jpg") in worker.processed_files
    assert restored["scan_type"] == "Solo Scan"
    visited = []

    def process(path, index):
        visited.append(path.name)
        return {"status": "no_match", "output_targets": []}

    worker._process_file = process
    worker.run()
    assert visited == ["two.jpg"]
    assert worker.processed_count == 2


def test_solo_copy_failure_is_not_counted_as_match(tmp_path, monkeypatch):
    worker = SoloScanWorker("scan", [], [{"id": "person"}], tmp_path / "out", tmp_path / "checkpoint",
                            MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setattr("domain.solo_worker.load_image", lambda path: (MagicMock(size=(100, 100)), None))
    worker.face_engine.detect_and_embed_faces.return_value = ([(0, 10, 10, 0)], [object()], [])
    worker.matcher.evaluate_solo_photo_matches = MagicMock(return_value=({"Person"}, []))
    worker.output_service.sanitize_folder_name.return_value = "Person"
    worker.output_service.get_destination_folder.return_value = tmp_path / "out" / "Person"
    worker.output_service.copy_photo_to_destination.return_value = (False, None, "Copy error: disk full")
    result = worker._process_file(tmp_path / "photo.jpg", 0)
    assert result["status"] == "error"
    assert worker.matched_count == 0
    assert worker.copied_file_pairs == []


def test_solo_cancel_waits_for_active_work_and_does_not_submit_rest(tmp_path, monkeypatch):
    started = threading.Event()
    release = threading.Event()
    processed = []
    worker = SoloScanWorker("scan", [tmp_path / f"{i}.jpg" for i in range(20)], [],
                            tmp_path / "out", tmp_path / "checkpoint.json", MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setattr("domain.solo_worker.os.cpu_count", lambda: 1)

    def process(file_path, index):
        started.set()
        release.wait(3)
        processed.append(file_path)
        return {"status": "cancelled"} if worker.is_cancelled else {"status": "no_match"}

    worker._process_file = process
    thread = threading.Thread(target=worker.run)
    thread.start()
    assert started.wait(2)
    worker.cancel()
    release.set()
    thread.join(5)
    assert not thread.is_alive()
    assert len(processed) <= 4  # Only the bounded in-flight tasks started.
    assert json.loads(worker.checkpoint_file.read_text())["status"] == "Cancelled"


def test_solo_summary_counts_only_successful_copies(tmp_path, monkeypatch):
    worker = SoloScanWorker("scan", [tmp_path / "good.jpg", tmp_path / "failed.jpg"], [],
                            tmp_path / "out", tmp_path / "checkpoint.json", MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setattr("domain.solo_worker.os.cpu_count", lambda: 1)

    def process(file_path, index):
        if file_path.name == "good.jpg":
            return {"status": "matched", "matched_names": {"Person"},
                    "copied_pairs": [(str(file_path), str(tmp_path / "out" / "good.jpg"))],
                    "output_targets": [str(tmp_path / "out" / "good.jpg")]}
        return {"status": "error", "error": "Copy error: disk full", "output_targets": ["Copy Status: disk full"]}

    worker._process_file = process
    results = []
    worker.finished_signal.connect(results.append)
    worker.run()
    summary = results[0]
    assert summary["status"] == "Completed"
    assert (summary["processed"], summary["matched"], summary["skipped"], summary["errors"]) == (2, 1, 1, 1)
    assert summary["results_by_person"] == {"Person": 1}
    assert len(summary["copied_file_pairs"]) == 1


def test_solo_pause_blocks_new_work_until_resumed(tmp_path, monkeypatch):
    worker = SoloScanWorker("scan", [tmp_path / "photo.jpg"], [], tmp_path / "out",
                            tmp_path / "checkpoint.json", MagicMock(), MagicMock(), MagicMock())
    monkeypatch.setattr("domain.solo_worker.os.cpu_count", lambda: 1)
    started = threading.Event()

    def process(file_path, index):
        started.set()
        return {"status": "no_match", "output_targets": []}

    worker._process_file = process
    worker.pause()
    thread = threading.Thread(target=worker.run)
    thread.start()
    assert not started.wait(0.3)
    worker.resume()
    thread.join(3)
    assert not thread.is_alive()
    assert started.is_set()


def test_solo_resume_dispatch_and_cancelled_move_never_prompts():
    from ui.main_window import MainWindow

    window = MagicMock()
    worker = MagicMock()
    window.solo_scan_service.resume_scan.return_value = (worker, {"scan_type": "Solo Scan"})
    MainWindow._on_resume_history_scan(window, "scan-id", "Solo Scan")
    window.solo_scan_service.resume_scan.assert_called_once_with("scan-id")
    window.scan_service.resume_scan.assert_not_called()
    window.page_processing.start_monitoring.assert_called_once_with(worker)

    MainWindow._on_scan_finished(window, {"scan_type": "Solo Scan", "status": "Cancelled",
                                          "operation_mode": "move", "copied_file_pairs": [("a", "b")]})
    window.solo_scan_service.verify_copied_photos.assert_not_called()
    window.scan_service.verify_copied_photos.assert_not_called()
