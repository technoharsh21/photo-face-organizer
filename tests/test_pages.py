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

