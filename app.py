"""
Photo Face Organizer Application Entry Point.

Initializes application services, face recognition engine, configuration,
and PySide6 QApplication main loop.
Disables bytecode caching (pycache) so changes are instantly reflected on every launch.
"""

import logging
import os
import sys
from pathlib import Path

# Disable Python bytecode (.pyc) caching to guarantee fresh code is loaded on every launch
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def _clean_pycache():
    """Remove cached __pycache__ folders and .pyc files on launch."""
    root = Path(__file__).parent
    for p in root.rglob("*.pyc"):
        try:
            p.unlink()
        except Exception:
            pass


if not getattr(sys, "frozen", False):
    _clean_pycache()

from PySide6.QtWidgets import QApplication

from config import Config
from domain.duplicate_detector import DuplicateDetector
from domain.face_engine import FaceRecognitionEngine
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from services.settings_service import SettingsService
from services.unknown_face_service import UnknownFaceService
from ui.main_window import MainWindow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Photo Face Organizer")

    config = Config()
    settings_service = SettingsService(config)

    device_pref = settings_service.get("device_preference", "Auto")
    face_engine = FaceRecognitionEngine(device_preference=device_pref)

    duplicate_detector = DuplicateDetector(config.duplicate_index_file)
    output_service = OutputService(duplicate_detector)

    profile_service = ProfileService(config, face_engine)
    unknown_face_service = UnknownFaceService(config, profile_service)
    history_service = HistoryService(config)

    scan_service = ScanService(
        config=config,
        face_engine=face_engine,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        profile_service=profile_service,
    )

    main_window = MainWindow(
        config=config,
        face_engine=face_engine,
        profile_service=profile_service,
        scan_service=scan_service,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        settings_service=settings_service,
    )

    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
