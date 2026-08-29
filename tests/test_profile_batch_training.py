"""
Unit tests for Batch Profile Training from Photo Folder.
"""

import tempfile
from pathlib import Path
from PIL import Image

from config import Config
from services.profile_service import ProfileService


class MockFaceEngineForBatch:
    def detect_faces(self, pil_img):
        return [(10, 40, 40, 10)]

    def extract_faces(self, pil_img, locations):
        return [pil_img.crop((10, 10, 40, 40))]

    def create_embeddings(self, pil_img, locations):
        import numpy as np
        return [np.ones(512, dtype=np.float64)]

    def calculate_match_score(self, emb1, emb2):
        return 85.0


def test_batch_add_reference_photos_from_folder():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = Config(app_data_dir=Path(tmp_dir))
        engine = MockFaceEngineForBatch()
        profile_service = ProfileService(config, engine)

        # Create profile with initial reference photo
        profile = profile_service.create_profile("Harsh Test")
        p_id = profile["id"]

        init_img = Path(tmp_dir) / "anchor.jpg"
        Image.new("RGB", (100, 100), color="red").save(init_img)
        profile_service.add_reference_photo(p_id, init_img)

        # Create temporary folder with 3 test images
        img_dir = Path(tmp_dir) / "test_photos"
        img_dir.mkdir(parents=True, exist_ok=True)

        for i in range(3):
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(img_dir / f"photo_{i}.jpg")

        added, total, msg = profile_service.batch_add_reference_photos_from_folder(p_id, img_dir)

        assert added == 3
        assert total == 3
        assert "Successfully trained profile" in msg

        updated = profile_service.get_profile(p_id)
        # 1 initial + 3 batch = 4
        assert len(updated.get("embeddings", [])) == 4
        assert len(updated.get("references", [])) == 4

        # Test outlier pruning
        removed, remaining = profile_service.prune_profile_outliers(p_id, min_similarity=60.0)
        assert removed == 0
        assert remaining == 4
