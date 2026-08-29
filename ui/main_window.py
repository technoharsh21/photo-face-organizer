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
from services.duplicate_service import DuplicateService
from services.face_cache_service import FaceCacheService
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from services.settings_service import SettingsService
from services.solo_scan_service import SoloScanService
from services.unknown_face_service import UnknownFaceService
from ui.components.crash_recovery_dialog import CrashRecoveryDialog
from ui.pages.dashboard_page import DashboardPage
from ui.pages.duplicate_page import DuplicatePage
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
        face_cache_service: FaceCacheService | None = None,
    ):
        super().__init__()
        self.config = config
        self.face_engine = face_engine
        self.profile_service = profile_service
        self.scan_service = scan_service
        self.face_cache_service = face_cache_service
        self.solo_scan_service = solo_scan_service or SoloScanService(
            config=config,
            face_engine=face_engine,
            output_service=output_service,
            unknown_face_service=unknown_face_service,
            history_service=history_service,
            profile_service=profile_service,
            face_cache_service=face_cache_service,
        )
        self.output_service = output_service
        self.unknown_face_service = unknown_face_service
        self.history_service = history_service
        self.settings_service = settings_service
        self.duplicate_service = DuplicateService(config)
        self.is_scanning_active = False

        self.setWindowTitle("Photo Face Organizer")
        self.resize(1100, 720)
        self.setMinimumSize(850, 560)
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
        self.page_settings = SettingsPage(self.settings_service, self.face_engine, self.face_cache_service)
        self.page_duplicates = DuplicatePage(self.duplicate_service)

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
            "Duplicates": (9, self.page_duplicates),
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
            (9, self.page_duplicates),
        ]:
            self.content_stack.addWidget(page_widget)

        # 2. Grouped Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(4)

        header_container = QVBoxLayout()
        app_title = QLabel("📸 Photo Face AI")
        app_title.setObjectName("AppTitle")
        app_sub = QLabel("InsightFace SCRFD + ArcFace")
        app_sub.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold; margin-top: -12px; margin-left: 16px; margin-bottom: 12px;")
        header_container.addWidget(app_title)
        header_container.addWidget(app_sub)
        sidebar_layout.addLayout(header_container)

        self.nav_button_group = QButtonGroup(self)
        self.nav_buttons: dict[str, QPushButton] = {}

        # Categorized Sidebar Sections
        sidebar_sections = [
            ("MAIN", [
                ("Dashboard", "🏠  Dashboard"),
                ("People", "👥  People Profiles"),
                ("New Scan", "🚀  New Scan Wizard"),
                ("Solo Scan", "🎯  Solo Scan (0% False)"),
            ]),
            ("LIBRARY & RESULTS", [
                ("Results", "📊  Results & Folders"),
                ("Unknown Faces", "❓  Unknown Faces"),
                ("Duplicates", "🔍  Duplicate Finder"),
                ("History", "📜  Scan History"),
            ]),
            ("SYSTEM", [
                ("Settings", "⚙️  Settings & GPU"),
            ])
        ]

        btn_index = 0
        for sec_title, sec_pages in sidebar_sections:
            sec_lbl = QLabel(f"<b>{sec_title}</b>")
            sec_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 800; margin-top: 10px; margin-left: 10px; letter-spacing: 1px;")
            sidebar_layout.addWidget(sec_lbl)

            for key, title in sec_pages:
                btn = QPushButton(title)
                btn.setProperty("class", "NavButton")
                btn.setCheckable(True)
                if btn_index == 0:
                    btn.setChecked(True)
                page_idx = self.page_map[key][0]
                self.nav_button_group.addButton(btn, page_idx)
                btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
                sidebar_layout.addWidget(btn)
                self.nav_buttons[key] = btn
                btn_index += 1

        sidebar_layout.addStretch()

        # System Status Indicator Box at Sidebar Bottom
        sys_status_box = QFrame()
        sys_status_box.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        sys_status_layout = QVBoxLayout(sys_status_box)
        sys_status_layout.setSpacing(4)

        self.lbl_sys_status = QLabel("● System Ready")
        self.lbl_sys_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

        self.lbl_hw_status = QLabel("🟢 AI Hardware: Active")
        self.lbl_hw_status.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 600;")
        self.update_hardware_status_badge()

        sys_status_layout.addWidget(self.lbl_sys_status)
        sys_status_layout.addWidget(self.lbl_hw_status)
        sidebar_layout.addWidget(sys_status_box)

        # Right Panel Container (TopBar + Content Stack)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #080c14; border-bottom: 1px solid #1e293b; padding: 12px 24px;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_topbar_title = QLabel("Dashboard")
        self.lbl_topbar_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        tb_layout.addWidget(self.lbl_topbar_title)

        tb_layout.addStretch()

        self.lbl_topbar_badge = QLabel("InsightFace AI Engine • 99.86% Precision")
        self.lbl_topbar_badge.setStyleSheet("background-color: #1e293b; color: #38bdf8; border: 1px solid #3b82f6; border-radius: 6px; padding: 4px 12px; font-weight: bold; font-size: 11px;")
        tb_layout.addWidget(self.lbl_topbar_badge)

        right_layout.addWidget(top_bar)
        right_layout.addWidget(self.content_stack, 1)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(right_container, 1)

        # Initial refresh
        self.page_dashboard.refresh()

    def update_hardware_status_badge(self):
        """Update hardware status badge at sidebar bottom."""
        if hasattr(self.face_engine, "get_device_info"):
            info = self.face_engine.get_device_info()
            dev = info.get("active_device", "Multi-Core CPU")
            if info.get("gpu_available"):
                self.lbl_hw_status.setText(f"🟢 GPU: {dev}")
            else:
                self.lbl_hw_status.setText(f"🟢 CPU: Multi-Core (Active)")

    def _set_navigation_enabled(self, enabled: bool):
        """Enable or disable sidebar navigation tabs during active scanning."""
        self.is_scanning_active = not enabled
        for btn in self.nav_buttons.values():
            btn.setEnabled(enabled)
            if not enabled:
                btn.setToolTip("Scan processing in progress. Cancel or wait for scan completion to switch tabs.")
            else:
                btn.setToolTip("")

        if not enabled:
            self.lbl_sys_status.setText("● Processing Photos")
            self.lbl_sys_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_sys_status.setText("● System Ready")
            self.lbl_sys_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

    def navigate_to(self, page_name: str):
        # Prevent tab switching during active scan unless navigating to Processing
        if self.is_scanning_active and page_name != "Processing" and page_name != "Results":
            return

        if page_name in self.page_map:
            idx, widget = self.page_map[page_name]
            self.content_stack.setCurrentIndex(idx)

            for key, btn in self.nav_buttons.items():
                btn.setChecked(key == page_name)

            self.lbl_topbar_title.setText(f"{page_name}")

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

            verified, count, verified_sources = self.scan_service.verify_copied_photos(copied_pairs)
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
                    del_count, err_count = self.scan_service.delete_verified_sources(verified_sources)
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
