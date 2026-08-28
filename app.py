"""
Photo Face Organizer Application Entry Point.

Initializes application services, face recognition engine, configuration,
logging to file/console, crash error hooks, and PySide6 QApplication main loop.
Disables bytecode caching (pycache) in dev mode.
"""

import io
import logging
import os
import sys
import traceback
from pathlib import Path

# PyInstaller --windowed mode sets sys.stdout/stderr to None on Windows.
# InsightFace/ONNX internally call print() which crashes with 'NoneType' has no attribute 'write'.
# Fix: replace None streams with real OS-level /dev/null file handles BEFORE any library imports.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

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

from PySide6.QtWidgets import QApplication, QMessageBox

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _setup_crash_logging(config: Config):
    """Setup persistent file logging and global uncaught exception crash handler."""
    log_file = config.app_data_dir / "photo_face_organizer.log"
    crash_file = config.app_data_dir / "crash_log.txt"

    try:
        config.app_data_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logging.getLogger().addHandler(file_handler)
    except Exception as e:
        print(f"Failed to initialize log file: {e}")

    def uncaught_exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        err_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.critical(f"Uncaught Exception:\n{err_str}")

        try:
            with open(crash_file, "w", encoding="utf-8") as f:
                f.write(err_str)
        except Exception:
            pass

        try:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Application Error")
            msg_box.setText("An unexpected error occurred.")
            msg_box.setInformativeText(f"Error details saved to:\n{crash_file}\n\nError: {exc_value}")
            msg_box.setDetailedText(err_str)
            msg_box.exec()
        except Exception:
            pass

    sys.excepthook = uncaught_exception_hook


from services.face_cache_service import FaceCacheService
from services.solo_scan_service import SoloScanService


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Photo Face Organizer")

    config = Config()
    _setup_crash_logging(config)

    settings_service = SettingsService(config)
    face_cache_service = FaceCacheService(config, settings_service)

    device_pref = settings_service.get("device_preference", "Auto")
    from domain.insight_engine import InsightFaceEngine
    face_engine = InsightFaceEngine(device_preference=device_pref)

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

    solo_scan_service = SoloScanService(
        config=config,
        face_engine=face_engine,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        profile_service=profile_service,
        face_cache_service=face_cache_service,
    )

    main_window = MainWindow(
        config=config,
        face_engine=face_engine,
        profile_service=profile_service,
        scan_service=scan_service,
        solo_scan_service=solo_scan_service,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        settings_service=settings_service,
        face_cache_service=face_cache_service,
    )

    main_window.show()
    sys.exit(app.exec())


import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
