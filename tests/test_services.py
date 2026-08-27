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
