"""
Unit tests for Find Photos by Person functionality.
Tests FindPhotosService, FindPhotosWorker, real-time match streaming, solo vs all matching, and safe file operations.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
from PIL import Image

from config import Config
from services.find_photos_service import FindPhotosService, FindPhotosWorker
from services.profile_service import ProfileService
from services.settings_service import SettingsService
from ui.components.photo_viewer_dialog import PhotoViewerDialog
from ui.pages.find_photos_page import FindPhotosPage



class MockFaceEngine:
    """Mock face engine for unit testing."""

    def detect_and_embed_faces(self, image):
        # Return 1 face location and 1 embedding by default
        locs = [(10, 50, 50, 10)]
        encs = [np.ones((512,), dtype=np.float64)]
        crops = [image]
        return locs, encs, crops

    def calculate_match_score(self, emb1, emb2):
        # If both are ones, return 90.0, else 30.0
        if np.allclose(emb1, emb2):
            return 90.0
        return 30.0


def test_find_photos_service_get_non_conflicting_path(tmp_path):
    service = FindPhotosService()
    target_dir = tmp_path / "saved_photos"
    target_dir.mkdir()

    # First file
    p1 = service.get_non_conflicting_path(target_dir, "photo.jpg")
    assert p1.name == "photo.jpg"
    p1.write_bytes(b"content1")

    # Second file with same name
    p2 = service.get_non_conflicting_path(target_dir, "photo.jpg")
    assert p2.name == "photo_1.jpg"
    p2.write_bytes(b"content2")

    # Third file
    p3 = service.get_non_conflicting_path(target_dir, "photo.jpg")
    assert p3.name == "photo_2.jpg"


def test_find_photos_service_save_single_and_multiple(tmp_path):
    service = FindPhotosService()

    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()

    img1 = src_dir / "img1.jpg"
    img2 = src_dir / "img2.jpg"
    img1.write_bytes(b"image 1 bytes")
    img2.write_bytes(b"image 2 bytes")

    # Test single save
    succ, dest_p, msg = service.save_single_photo(str(img1), dest_dir)
    assert succ is True
    assert dest_p is not None
    assert dest_p.exists()
    assert dest_p.read_bytes() == b"image 1 bytes"
    assert img1.exists()  # Original unchanged

    # Test multiple save
    succ_cnt, err_cnt, saved_paths = service.save_multiple_photos([str(img1), str(img2)], dest_dir)
    assert succ_cnt == 2
    assert err_cnt == 0
    assert len(saved_paths) == 2
    for sp in saved_paths:
        assert sp.exists()


def test_find_photos_worker_all_photos_matching(tmp_path):
    # Setup test images
    folder = tmp_path / "photos"
    folder.mkdir()

    img_path = folder / "sample.jpg"
    # Create valid JPEG
    pil = Image.new("RGB", (100, 100), color="blue")
    pil.save(img_path)

    profile = {
        "id": "p_123",
        "name": "Harsh",
        "embeddings": [np.ones((512,)).tolist()],
        "centroid_embedding": np.ones((512,)).tolist(),
    }

    mock_engine = MockFaceEngine()

    worker = FindPhotosWorker(
        target_profile=profile,
        folders=[folder],
        match_type="all",
        recursive=True,
        threshold=50.0,
        face_engine=mock_engine,
    )

    matches_emitted = []
    worker.match_found_signal.connect(lambda m: matches_emitted.append(m))

    finished_data = []
    worker.finished_signal.connect(lambda s, m, t, all_m: finished_data.append((s, m, t, all_m)))

    worker.run()

    assert len(matches_emitted) == 1
    assert matches_emitted[0]["filename"] == "sample.jpg"
    assert matches_emitted[0]["match_score"] == 90.0
    assert len(finished_data) == 1
    assert finished_data[0][1] == 1  # 1 match found


def test_find_photos_worker_solo_filtering(tmp_path):
    folder = tmp_path / "photos"
    folder.mkdir()

    img_path = folder / "group.jpg"
    pil = Image.new("RGB", (100, 100), color="red")
    pil.save(img_path)

    profile = {
        "id": "p_123",
        "name": "Harsh",
        "embeddings": [np.ones((512,)).tolist()],
    }

    class MultiFaceEngine(MockFaceEngine):
        def detect_and_embed_faces(self, image):
            # Return 2 faces (group photo)
            locs = [(10, 30, 30, 10), (40, 60, 60, 40)]
            encs = [np.ones((512,)), np.zeros((512,))]
            return locs, encs, [image, image]

    mock_engine = MultiFaceEngine()

    # In "solo" mode, group photo with 2 faces must be REJECTED
    worker_solo = FindPhotosWorker(
        target_profile=profile,
        folders=[folder],
        match_type="solo",
        threshold=50.0,
        face_engine=mock_engine,
    )

    matches_solo = []
    worker_solo.match_found_signal.connect(lambda m: matches_solo.append(m))
    worker_solo.run()

    assert len(matches_solo) == 0  # Replaced/rejected because it's a group photo

    # In "all" mode, group photo containing the face MUST be ACCEPTED
    worker_all = FindPhotosWorker(
        target_profile=profile,
        folders=[folder],
        match_type="all",
        threshold=50.0,
        face_engine=mock_engine,
    )

    matches_all = []
    worker_all.match_found_signal.connect(lambda m: matches_all.append(m))
    worker_all.run()

    assert len(matches_all) == 1
    assert matches_all[0]["filename"] == "group.jpg"


def test_find_photos_worker_cancellation(tmp_path):
    folder = tmp_path / "photos"
    folder.mkdir()

    for i in range(5):
        img_path = folder / f"test_{i}.jpg"
        pil = Image.new("RGB", (50, 50), color="green")
        pil.save(img_path)

    profile = {
        "id": "p_123",
        "name": "Harsh",
        "embeddings": [np.ones((512,)).tolist()],
    }

    worker = FindPhotosWorker(
        target_profile=profile,
        folders=[folder],
        match_type="all",
        face_engine=MockFaceEngine(),
    )

    worker.cancel()
    worker.run()

    assert len(worker.matches) == 0


import sys
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_photo_viewer_dialog_navigation(qapp, tmp_path):
    f1 = tmp_path / "photo1.jpg"
    f2 = tmp_path / "photo2.jpg"
    Image.new("RGB", (100, 100), color="blue").save(f1)
    Image.new("RGB", (100, 100), color="red").save(f2)

    photos_list = [
        {"path": str(f1), "filename": "photo1.jpg", "match_score": 95.0},
        {"path": str(f2), "filename": "photo2.jpg", "match_score": 88.0},
    ]

    dialog = PhotoViewerDialog(photos_list=photos_list, initial_index=0)
    assert dialog.current_index == 0
    assert "photo1.jpg" in dialog.lbl_title.text()

    # Next photo
    dialog._next_photo()
    assert dialog.current_index == 1
    assert "photo2.jpg" in dialog.lbl_title.text()

    # Prev photo
    dialog._prev_photo()
    assert dialog.current_index == 0
    assert "photo1.jpg" in dialog.lbl_title.text()

    # Zoom and rotation functions
    dialog._zoom_in()
    dialog._zoom_out()
    dialog._fit_to_window()
    dialog._actual_size()
    dialog._rotate()
    dialog._rotate_left()
    dialog._rotate_right()


def test_find_photos_page_step_transitions(qapp, tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    mock_engine = MockFaceEngine()
    profile_svc = ProfileService(config, mock_engine)
    settings_svc = SettingsService(config)

    # Create dummy profile
    p_data = profile_svc.create_profile("Harsh")
    assert p_data is not None

    page = FindPhotosPage(
        profile_service=profile_svc,
        face_engine=mock_engine,
        settings_service=settings_svc,
    )

    # Step 1: People selection
    page._goto_step1()
    assert page.wizard_stack.currentIndex() == 0

    page._on_person_card_clicked(p_data["id"])
    assert page.btn_step1_next.isEnabled() is True

    # Step 2: Folder selection
    page._goto_step2()
    assert page.wizard_stack.currentIndex() == 1
    assert "Harsh" in page.lbl_step2_person_name.text()

    # Add folder
    test_dir = tmp_path / "test_photos"
    test_dir.mkdir()
    page.selected_folders = [str(test_dir)]
    page._update_folders_list_view()
    assert page.btn_step2_next.isEnabled() is True

    # Step 3: Match mode selection
    page._goto_step3()
    assert page.wizard_stack.currentIndex() == 2
    page._select_match_mode("solo")
    assert page.match_mode == "solo"
    page._select_match_mode("all")
    assert page.match_mode == "all"

