"""
Tests for Application Services (Profiles, Scans, Unknown Faces, History).
"""

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from config import Config
from domain.face_engine import FaceEngine
from services.profile_service import ProfileService
from services.unknown_face_service import UnknownFaceService


class MockFaceEngine(FaceEngine):
    def detect_faces(self, image, model="hog"):
        return [(10, 50, 60, 10)]

    def extract_faces(self, image, face_locations=None):
        return [Image.new("RGB", (40, 50), color="red")]

    def create_embeddings(self, image, face_locations=None):
        return [np.zeros(128)]

    def compare_embeddings(self, embedding1, embedding2):
        return 0.0

    def calculate_match_score(self, embedding1, embedding2):
        return 100.0

    def set_device_preference(self, preference):
        return "CPU"

    def get_device_info(self):
        return {"requested_device": "CPU", "active_device": "CPU", "gpu_available": False, "model_used": "hog"}


def test_profile_creation_and_reference_addition():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config(app_data_dir=Path(tmp_dir))
        engine = MockFaceEngine()
        p_svc = ProfileService(config, engine)

        # Create profile
        p = p_svc.create_profile("Harsh")
        assert p["name"] == "Harsh"

        # Create dummy image file
        ref_path = Path(tmp_dir) / "test_ref.jpg"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(ref_path)

        success, msg = p_svc.add_reference_photo(p["id"], ref_path, selected_face_index=0)
        assert success is True

        updated_p = p_svc.get_profile(p["id"])
        assert len(updated_p["references"]) == 1
        assert len(updated_p["embeddings"]) == 1


def test_profile_validations():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config(app_data_dir=Path(tmp_dir))
        engine = MockFaceEngine()
        p_svc = ProfileService(config, engine)

        # 1. Test empty name validation
        import pytest
        with pytest.raises(ValueError, match="empty"):
            p_svc.create_profile("   ")

        # 2. Test duplicate profile name validation
        p_svc.create_profile("Harsh")
        with pytest.raises(ValueError, match="already exists"):
            p_svc.create_profile("harsh")

        # 3. Test 0 faces validation
        class NoFaceEngine(MockFaceEngine):
            def detect_faces(self, image, model="hog"):
                return []

        p_svc_no_face = ProfileService(config, NoFaceEngine())
        p = p_svc_no_face.get_profile(p_svc_no_face.list_profiles()[0]["id"])
        img_path = Path(tmp_dir) / "no_face.jpg"
        Image.new("RGB", (100, 100)).save(img_path)

        success, msg = p_svc_no_face.add_reference_photo(p["id"], img_path)
        assert success is False
        assert "No face detected" in msg


def test_scan_service_move_mode_verification(tmp_path):
    src_dir = tmp_path / "sources"
    tgt_dir = tmp_path / "target"
    src_dir.mkdir()
    tgt_dir.mkdir()

    src_file = src_dir / "photo.jpg"
    tgt_file = tgt_dir / "photo.jpg"

    data = b"image content 12345"
    src_file.write_bytes(data)
    tgt_file.write_bytes(data)

    from services.history_service import HistoryService
    from services.output_service import OutputService
    from domain.duplicate_detector import DuplicateDetector
    from services.scan_service import ScanService

    cfg = Config(app_data_dir=tmp_path / "appdata")
    fe = MockFaceEngine()
    dd = DuplicateDetector(cfg.duplicate_index_file)
    ops = OutputService(dd)
    ps = ProfileService(cfg, fe)
    ufs = UnknownFaceService(cfg, ps)
    hs = HistoryService(cfg)

    scan_svc = ScanService(cfg, fe, ops, ufs, hs, ps)

    copied_pairs = [(str(src_file), str(tgt_file))]

    verified, count, verified_sources = scan_svc.verify_copied_photos(copied_pairs)
    assert verified is True
    assert count == 1
    assert str(src_file) in verified_sources

    del_count, err_count = scan_svc.delete_verified_sources(verified_sources)
    assert del_count == 1
    assert err_count == 0
    assert not src_file.exists()
    assert tgt_file.exists()

def test_unknown_face_grouping_and_conversion():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config(app_data_dir=Path(tmp_dir))
        engine = MockFaceEngine()
        p_svc = ProfileService(config, engine)
        u_svc = UnknownFaceService(config, p_svc)

        crop = Image.new("RGB", (50, 50), color="green")
        emb = np.zeros(128)

        # Store two unknown faces
        u1 = u_svc.store_unknown_face(crop, emb, "photo1.jpg", [0, 50, 50, 0], "scan_1")
        u2 = u_svc.store_unknown_face(crop, emb, "photo2.jpg", [0, 50, 50, 0], "scan_1")

        groups = u_svc.group_unknown_faces(threshold=50.0)
        assert len(groups) == 1
        assert len(groups[0]["faces"]) == 2

        # Convert group to profile
        p = u_svc.convert_group_to_profile(groups[0]["group_id"], "Converted Person")
        assert p is not None
        assert p["name"] == "Converted Person"

        # Unknown faces should be cleared
        remaining = u_svc.list_unknown_faces()
        assert len(remaining) == 0


def test_delete_unknown_group():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config(app_data_dir=Path(tmp_dir))
        engine = MockFaceEngine()
        p_svc = ProfileService(config, engine)
        u_svc = UnknownFaceService(config, p_svc)

        crop = Image.new("RGB", (50, 50), color="green")
        emb = np.zeros(128)

        u1 = u_svc.store_unknown_face(crop, emb, "photo1.jpg", [0, 50, 50, 0], "scan_1")
        u2 = u_svc.store_unknown_face(crop, emb, "photo2.jpg", [0, 50, 50, 0], "scan_1")

        groups = u_svc.group_unknown_faces(threshold=50.0)
        assert len(groups) == 1
        g_id = groups[0]["group_id"]

        del_cnt = u_svc.delete_group(g_id)
        assert del_cnt == 2
        assert len(u_svc.list_unknown_faces()) == 0
