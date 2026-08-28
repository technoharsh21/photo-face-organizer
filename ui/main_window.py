"""
Main Window Module for Photo Face Organizer.

Assembles sidebar navigation, page switching stacked widget, crash recovery prompt,
and central application workflow.
Locks navigation tabs during active scanning to prevent tab switching during processing.
"""

from typing import Any

from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import Config
from domain.face_engine import FaceEngine
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from services.settings_service import SettingsService
from services.unknown_face_service import UnknownFaceService
from services.solo_scan_service import SoloScanService
from ui.components.crash_recovery_dialog import CrashRecoveryDialog
from ui.pages.dashboard_page import DashboardPage
from ui.pages.history_page import HistoryPage
from ui.pages.new_scan_page import NewScanPage
from ui.pages.people_page import PeoplePage
from ui.pages.processing_page import ProcessingPage
from ui.pages.results_page import ResultsPage
from ui.pages.settings_page import SettingsPage
from ui.pages.solo_scan_page import SoloScanPage
from ui.pages.unknown_faces_page import UnknownFacesPage
from ui.styles import STYLESHEET


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(
        self,
        config: Config,
        face_engine: FaceEngine,
        profile_service: ProfileService,
        scan_service: ScanService,
        output_service: OutputService,
        unknown_face_service: UnknownFaceService,
        history_service: HistoryService,
        settings_service: SettingsService,
        solo_scan_service: SoloScanService | None = None,
    ):
        super().__init__()
        self.config = config
        self.face_engine = face_engine
        self.profile_service = profile_service
        self.scan_service = scan_service
        self.solo_scan_service = solo_scan_service or SoloScanService(
            config=config,
            face_engine=face_engine,
            output_service=output_service,
            unknown_face_service=unknown_face_service,
            history_service=history_service,
            profile_service=profile_service,
        )
        self.output_service = output_service
        self.unknown_face_service = unknown_face_service
        self.history_service = history_service
        self.settings_service = settings_service
        self.is_scanning_active = False

        self.setWindowTitle("Photo Face Organizer")
        self.resize(1100, 720)
        self.setStyleSheet(STYLESHEET)

        self._setup_ui()
        self._check_interrupted_scans()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Main Content Stacked Widget & Pages
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentFrame")

        self.page_dashboard = DashboardPage(self.profile_service, self.history_service, self.unknown_face_service, self.navigate_to)
        self.page_people = PeoplePage(self.profile_service)
        self.page_new_scan = NewScanPage(self.profile_service, self.scan_service, self.settings_service, self._on_scan_started)
        self.page_solo_scan = SoloScanPage(self.profile_service, self.solo_scan_service, self.settings_service, self._on_scan_started)
        self.page_processing = ProcessingPage(self.scan_service, self._on_scan_finished)
        self.page_results = ResultsPage(self.profile_service, self.output_service)
        self.page_unknown_faces = UnknownFacesPage(self.unknown_face_service)
        self.page_history = HistoryPage(self.history_service, self.scan_service, self._on_view_history_results, self._on_resume_history_scan)
        self.page_settings = SettingsPage(self.settings_service, self.face_engine)

        self.page_map = {
            "Dashboard": (0, self.page_dashboard),
            "People": (1, self.page_people),
            "New Scan": (2, self.page_new_scan),
            "Solo Scan": (3, self.page_solo_scan),
            "Processing": (4, self.page_processing),
            "Results": (5, self.page_results),
            "Unknown Faces": (6, self.page_unknown_faces),
            "History": (7, self.page_history),
            "Settings": (8, self.page_settings),
        }

        for idx, page_widget in [
            (0, self.page_dashboard),
            (1, self.page_people),
            (2, self.page_new_scan),
            (3, self.page_solo_scan),
            (4, self.page_processing),
            (5, self.page_results),
            (6, self.page_unknown_faces),
            (7, self.page_history),
            (8, self.page_settings),
        ]:
            self.content_stack.addWidget(page_widget)

        # 2. Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(6)

        app_title = QLabel("📸 Face Organizer")
        app_title.setObjectName("AppTitle")
        sidebar_layout.addWidget(app_title)

        self.nav_button_group = QButtonGroup(self)
        self.nav_buttons: dict[str, QPushButton] = {}

        pages = [
            ("Dashboard", "📊 Dashboard"),
            ("People", "👥 People"),
            ("New Scan", "🚀 New Scan"),
            ("Solo Scan", "👤 Solo Scan"),
            ("Results", "🎯 Results"),
            ("Unknown Faces", "❓ Unknown Faces"),
            ("History", "📜 History"),
            ("Settings", "⚙️ Settings"),
        ]

        for i, (key, title) in enumerate(pages):
            btn = QPushButton(title)
            btn.setProperty("class", "NavButton")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            page_idx = self.page_map[key][0]
            self.nav_button_group.addButton(btn, page_idx)
            btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[key] = btn

        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.content_stack)

        # Initial refresh
        self.page_dashboard.refresh()

    def _set_navigation_enabled(self, enabled: bool):
        """Enable or disable sidebar navigation tabs during active scanning."""
        self.is_scanning_active = not enabled
        for btn in self.nav_buttons.values():
            btn.setEnabled(enabled)
            if not enabled:
                btn.setToolTip("Scan processing in progress. Cancel or wait for scan completion to switch tabs.")
            else:
                btn.setToolTip("")

    def navigate_to(self, page_name: str):
        # Prevent tab switching during active scan unless navigating to Processing
        if self.is_scanning_active and page_name != "Processing" and page_name != "Results":
            return

        if page_name in self.page_map:
            idx, widget = self.page_map[page_name]
            self.content_stack.setCurrentIndex(idx)

            for key, btn in self.nav_buttons.items():
                btn.setChecked(key == page_name)

            if hasattr(widget, "refresh"):
                widget.refresh()

    def _check_interrupted_scans(self):
        """Startup check for interrupted scans."""
        interrupted = self.scan_service.check_interrupted_scans()
        if interrupted:
            scan_data = interrupted[0]
            dlg = CrashRecoveryDialog(self, scan_data)
            dlg.exec()

            action = dlg.chosen_action
            scan_id = scan_data.get("scan_id")

            if action == "resume":
                self._on_resume_history_scan(scan_id)
            elif action == "restart":
                self.navigate_to("New Scan")
            else:  # discard
                self.scan_service.discard_recovery(scan_id)

    def _on_scan_started(self, worker, scan_meta):
        self._set_navigation_enabled(False)
        self.navigate_to("Processing")
        self.page_processing.start_monitoring(worker)

    def _on_scan_finished(self, summary: dict[str, Any]):
        self._set_navigation_enabled(True)

        # Handle Move Mode (Copy -> Verify 100% -> Confirm Delete Original Source Files)
        op_mode = summary.get("operation_mode")
        copied_pairs = summary.get("copied_file_pairs", [])

        if op_mode == "move" and copied_pairs:
            from PySide6.QtWidgets import QMessageBox

            verified, count, verified_sources = self.solo_scan_service.verify_copied_photos(copied_pairs)
            if verified and count > 0:
                answer = QMessageBox.question(
                    self,
                    "100% Verification Successful",
                    f"All {count} photos have been successfully copied and verified in your output directory.\n\n"
                    f"Do you want to delete the original source photos from your source folder now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer == QMessageBox.Yes:
                    del_count, err_count = self.solo_scan_service.delete_verified_sources(verified_sources)
                    QMessageBox.information(
                        self,
                        "Source Photos Cleaned",
                        f"Successfully deleted {del_count} verified original source photos from disk.",
                    )
            elif not verified:
                QMessageBox.warning(
                    self,
                    "Verification Warning",
                    "Some copied files could not be 100% verified on disk. Original source files have NOT been deleted for safety.",
                )

        self.page_results.load_results(summary)
        self.navigate_to("Results")

    def _on_view_history_results(self, scan_data: dict[str, Any]):
        self.page_results.load_results(scan_data)
        self.navigate_to("Results")

    def _on_resume_history_scan(self, scan_id: str):
        res = self.scan_service.resume_scan(scan_id)
        if res:
            worker, scan_meta = res
            self._set_navigation_enabled(False)
            self.navigate_to("Processing")
            self.page_processing.start_monitoring(worker)

    def _on_view_history_results(self, scan_data: dict[str, Any]):
        self.page_results.load_results(scan_data)
        self.navigate_to("Results")

    def _on_resume_history_scan(self, scan_id: str):
        res = self.scan_service.resume_scan(scan_id)
        if res:
            worker, scan_meta = res
            self._set_navigation_enabled(False)
            self.navigate_to("Processing")
            self.page_processing.start_monitoring(worker)
