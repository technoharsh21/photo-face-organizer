"""
Tests for UI Page Initialization and Navigation.

Ensures all 8 main application pages load without error, contain real controls,
and navigation works smoothly.
"""

import sys

import pytest
from PySide6.QtWidgets import QApplication

from config import Config
from domain.duplicate_detector import DuplicateDetector
from domain.insight_engine import InsightFaceEngine
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from services.settings_service import SettingsService
from services.unknown_face_service import UnknownFaceService
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_all_pages_load_and_navigate(qapp, tmp_path):
    config = Config(app_data_dir=tmp_path)
    settings = SettingsService(config)

    # Use CPU mode for test runner
    engine = InsightFaceEngine(device_preference="CPU")

    detector = DuplicateDetector(config.duplicate_index_file)
    output_svc = OutputService(detector)
    profile_svc = ProfileService(config, engine)
    unknown_svc = UnknownFaceService(config, profile_svc)
    history_svc = HistoryService(config)

    scan_svc = ScanService(
        config=config,
        face_engine=engine,
        output_service=output_svc,
        unknown_face_service=unknown_svc,
        history_service=history_svc,
        profile_service=profile_svc,
    )

    window = MainWindow(
        config=config,
        face_engine=engine,
        profile_service=profile_svc,
        scan_service=scan_svc,
        output_service=output_svc,
        unknown_face_service=unknown_svc,
        history_service=history_svc,
        settings_service=settings,
    )

    # Verify all 10 pages exist and can be navigated to
    pages = [
        "Dashboard", "People", "New Scan", "Solo Scan",
        "Processing", "Results", "Unknown Faces", "History",
        "Settings", "Duplicates"
    ]

    for page_name in pages:
        window.navigate_to(page_name)
        assert window.content_stack.currentWidget() is not None

    # Test Dashboard specific components
    dashboard = window.page_dashboard
    assert dashboard is not None
    assert dashboard.card_profiles["val_lbl"].text() == "0"
    assert dashboard.card_processed["val_lbl"].text() == "0"

    # Create a profile and refresh dashboard
    profile_svc.create_profile("Alice")
    dashboard.refresh()
    assert dashboard.card_profiles["val_lbl"].text() == "1"
    assert dashboard.profiles_layout.count() > 0

    # Test Window Icon is set
    assert not window.windowIcon().isNull()


def test_results_page_nested_subfolders(qapp, tmp_path):
    from domain.duplicate_detector import DuplicateDetector
    from services.output_service import OutputService
    from services.profile_service import ProfileService
    from ui.pages.results_page import ResultsPage

    detector = DuplicateDetector(tmp_path / "index.json")
    output_svc = OutputService(detector)
    config = Config(app_data_dir=tmp_path)
    profile_svc = ProfileService(config, None)

    results_page = ResultsPage(profile_svc, output_svc)

    out_dir = tmp_path / "Output"
    alice_date_dir = out_dir / "Alice" / "2026" / "2026-02-19"
    alice_date_dir.mkdir(parents=True, exist_ok=True)
    (alice_date_dir / "IMG_001.jpg").write_bytes(b"dummy image 1")
    (alice_date_dir / "IMG_002.jpg").write_bytes(b"dummy image 2")

    bob_dir = out_dir / "Bob"
    bob_dir.mkdir(parents=True, exist_ok=True)
    (bob_dir / "IMG_003.jpg").write_bytes(b"dummy image 3")

    summary = {
        "output_dir": str(out_dir),
        "results_by_person": {"Alice": 2, "Bob": 1},
        "processed": 3,
        "matched": 3,
        "no_match": 0,
        "unknown_faces": 0,
    }

    results_page.load_results(summary)

    # Top level should have Alice and Bob
    assert results_page.tree.topLevelItemCount() == 2

    # Find Alice item
    alice_item = None
    for i in range(results_page.tree.topLevelItemCount()):
        item = results_page.tree.topLevelItem(i)
        if "Alice" in item.text(0):
            alice_item = item
            break

    assert alice_item is not None
    assert "2 photos" in alice_item.text(1)
    assert alice_item.childCount() == 1  # 2026 folder

    year_item = alice_item.child(0)
    assert "2026" in year_item.text(0)
    assert year_item.childCount() == 1  # 2026-02-19 folder

    date_item = year_item.child(0)
    assert "2026-02-19" in date_item.text(0)
    assert date_item.childCount() == 2  # 2 photos


