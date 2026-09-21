"""
Main Window Module for Photo Face Organizer.

Assembles sidebar navigation, page switching stacked widget, crash recovery prompt,
and central application workflow.
Locks navigation tabs during active scanning to prevent tab switching during processing.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QGraphicsOpacityEffect,
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
from ui.components.icons import get_icon
from ui.components.onboarding_tour import OnboardingTour, TourStep
from ui.components.toast_notification import ToastManager
from ui.pages.dashboard_page import DashboardPage
from ui.pages.duplicate_page import DuplicatePage
from ui.pages.find_photos_page import FindPhotosPage
from ui.pages.history_page import HistoryPage
from ui.pages.new_scan_page import NewScanPage
from ui.pages.people_page import PeoplePage
from ui.pages.processing_page import ProcessingPage
from ui.pages.results_page import ResultsPage
from ui.pages.settings_page import SettingsPage
from ui.pages.solo_scan_page import SoloScanPage
from ui.pages.unknown_faces_page import UnknownFacesPage
from ui.styles import get_stylesheet


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
        self.setStyleSheet(get_stylesheet())

        # Set Window Icon
        root_dir = Path(__file__).resolve().parent.parent
        icon_path = root_dir / "icon.png"
        if not icon_path.exists():
            icon_path = root_dir / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._setup_ui()
        self._check_interrupted_scans()
        self.navigate_to("Dashboard")

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Main Content Stacked Widget & Pages
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentFrame")

        self.page_dashboard = DashboardPage(
            profile_service=self.profile_service,
            history_service=self.history_service,
            unknown_face_service=self.unknown_face_service,
            navigate_cb=self.navigate_to,
            settings_service=self.settings_service,
            face_engine=self.face_engine,
        )
        self.page_people = PeoplePage(self.profile_service, self.face_engine)
        self.page_find_photos = FindPhotosPage(
            profile_service=self.profile_service,
            face_engine=self.face_engine,
            settings_service=self.settings_service,
            face_cache_service=self.face_cache_service,
            navigate_cb=self.navigate_to,
        )
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
            "Find Photos": (2, self.page_find_photos),
            "New Scan": (3, self.page_new_scan),
            "Solo Scan": (4, self.page_solo_scan),
            "Processing": (5, self.page_processing),
            "Results": (6, self.page_results),
            "Unknown Faces": (7, self.page_unknown_faces),
            "History": (8, self.page_history),
            "Settings": (9, self.page_settings),
            "Duplicates": (10, self.page_duplicates),
        }

        for idx, page_widget in [
            (0, self.page_dashboard),
            (1, self.page_people),
            (2, self.page_find_photos),
            (3, self.page_new_scan),
            (4, self.page_solo_scan),
            (5, self.page_processing),
            (6, self.page_results),
            (7, self.page_unknown_faces),
            (8, self.page_history),
            (9, self.page_settings),
            (10, self.page_duplicates),
        ]:
            self.content_stack.addWidget(page_widget)

        # 2. Grouped Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 14, 12, 14)
        sidebar_layout.setSpacing(4)

        header_container = QVBoxLayout()
        header_container.setSpacing(2)

        # Brand row: [stretchL, icon, title+sub, stretchR] — stretch factors are
        # flipped in _apply_sidebar_collapsed to center the brand when collapsed.
        header_top = QHBoxLayout()
        header_top.setContentsMargins(4, 4, 4, 0)
        header_top.setSpacing(10)

        root_dir = Path(__file__).resolve().parent.parent
        icon_path = root_dir / "icon.png"
        if not icon_path.exists():
            icon_path = root_dir / "icon.ico"

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(26, 26)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)

        self.app_title = QLabel("Photo Face AI")
        self.app_title.setObjectName("AppTitle")
        self.app_title.setStyleSheet("padding: 0px; font-size: 16px; font-weight: 800; color: #ffffff;")
        self.app_sub = QLabel("InsightFace SCRFD + ArcFace")
        self.app_sub.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.addWidget(self.app_title)
        title_col.addWidget(self.app_sub)
        self._brand_text = QWidget()
        self._brand_text.setLayout(title_col)

        header_top.addStretch()  # idx 0
        header_top.addWidget(icon_lbl)  # idx 1
        header_top.addWidget(self._brand_text)  # idx 2
        header_top.addStretch()  # idx 3
        self._header_top_row = header_top
        header_top.setStretch(0, 0)
        header_top.setStretch(3, 1)  # expanded: brand left-aligned

        # Toggle lives on its own row so it never competes with the brand for
        # width; centered when collapsed, right-aligned when expanded.
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(4, 2, 4, 0)
        self.btn_sidebar_toggle = QPushButton()
        self.btn_sidebar_toggle.setObjectName("SidebarToggle")
        self.btn_sidebar_toggle.setIcon(get_icon("chevron_left", color="#94a3b8", size=16))
        self.btn_sidebar_toggle.setIconSize(QSize(16, 16))
        self.btn_sidebar_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_sidebar_toggle.setToolTip("Collapse sidebar")
        self.btn_sidebar_toggle.clicked.connect(self._toggle_sidebar)
        toggle_row.addStretch()  # idx 0
        toggle_row.addWidget(self.btn_sidebar_toggle)  # idx 1
        toggle_row.addStretch()  # idx 2
        self._toggle_row = toggle_row
        toggle_row.setStretch(0, 1)
        toggle_row.setStretch(2, 0)  # expanded: toggle right

        header_container.addLayout(header_top)
        header_container.addLayout(toggle_row)
        sidebar_layout.addLayout(header_container)

        self.nav_button_group = QButtonGroup(self)
        self.nav_buttons: dict[str, QPushButton] = {}
        self._nav_labels: dict[str, str] = {}
        self._nav_tooltips: dict[str, str] = {}
        self._section_labels: list[QLabel] = []
        self._fade_anims: dict[QWidget, QPropertyAnimation] = {}
        self._sidebar_collapsed = False

        # Categorized Sidebar Sections: (key, label, icon, shortcut)
        sidebar_sections = [
            ("MAIN", [
                ("Dashboard", "Dashboard", "home", "Ctrl+D"),
                ("People", "People Profiles", "users", "Ctrl+P"),
                ("Find Photos", "Find Photos by Person", "search", "Ctrl+F"),
                ("New Scan", "New Scan Wizard", "rocket", "Ctrl+N"),
                ("Solo Scan", "Solo Scan (0% False)", "target", "Ctrl+Shift+N"),
            ]),
            ("LIBRARY & RESULTS", [
                ("Results", "Results & Folders", "pie_chart", "Ctrl+R"),
                ("Unknown Faces", "Unknown Faces", "question_circle", "Ctrl+U"),
                ("Duplicates", "Duplicate Finder", "copy", ""),
                ("History", "Scan History", "history", "Ctrl+H"),
            ]),
            ("SYSTEM", [
                ("Settings", "Settings", "settings", "Ctrl+,"),
            ])
        ]

        btn_index = 0
        for sec_title, sec_pages in sidebar_sections:
            sec_lbl = QLabel(f"<b>{sec_title}</b>")
            sec_lbl.setObjectName("SectionLabel")
            sidebar_layout.addWidget(sec_lbl)
            self._section_labels.append(sec_lbl)

            for key, label, icon_name, shortcut in sec_pages:
                btn = QPushButton(label)
                btn.setProperty("class", "NavButton")
                btn.setIcon(get_icon(icon_name, color="#94a3b8", size=18))
                btn.setIconSize(QSize(18, 18))
                btn.setCheckable(True)
                if btn_index == 0:
                    btn.setChecked(True)
                tooltip = f"{label}  ({shortcut})" if shortcut else label
                btn.setToolTip(tooltip)
                self._nav_tooltips[key] = tooltip
                self._nav_labels[key] = label
                page_idx = self.page_map[key][0]
                self.nav_button_group.addButton(btn, page_idx)
                btn.clicked.connect(lambda _, k=key: self.navigate_to(k))
                sidebar_layout.addWidget(btn)
                self.nav_buttons[key] = btn
                btn_index += 1

        sidebar_layout.addStretch()

        # System Status Indicator Box at Sidebar Bottom
        self.sys_status_box = QFrame()
        self.sys_status_box.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        sys_status_layout = QVBoxLayout(self.sys_status_box)
        sys_status_layout.setSpacing(4)

        self.lbl_sys_status = QLabel("● System Ready")
        self.lbl_sys_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

        self.lbl_hw_status = QLabel("🟢 AI Hardware: Active")
        self.lbl_hw_status.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 600;")
        self.update_hardware_status_badge()

        sys_status_layout.addWidget(self.lbl_sys_status)
        sys_status_layout.addWidget(self.lbl_hw_status)
        sidebar_layout.addWidget(self.sys_status_box)

        # Sidebar width is owned by Python so it can be animated on collapse
        self.sidebar = sidebar
        sidebar.setMinimumWidth(235)
        sidebar.setMaximumWidth(235)

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
        self.right_container = right_container

        # Toast notifications anchored bottom-right of the content area
        self.toasts = ToastManager(right_container)

        self._setup_shortcuts()

        # Initial refresh
        self.page_dashboard.refresh()
        QTimer.singleShot(700, self._maybe_start_tour)

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
        for key, btn in self.nav_buttons.items():
            btn.setEnabled(enabled)
            if not enabled:
                btn.setToolTip("Scan processing in progress. Cancel or wait for scan completion to switch tabs.")
            else:
                btn.setToolTip(self._nav_tooltips.get(key, ""))

        if not enabled:
            self.lbl_sys_status.setText("● Processing Photos")
            self.lbl_sys_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_sys_status.setText("● System Ready")
            self.lbl_sys_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")

    def navigate_to(self, page_name: str, force_refresh: bool = False):
        # Prevent tab switching during active scan unless navigating to Processing
        if self.is_scanning_active and page_name != "Processing" and page_name != "Results":
            return

        if page_name in self.page_map:
            idx, widget = self.page_map[page_name]
            changed = self.content_stack.currentIndex() != idx
            self.content_stack.setCurrentIndex(idx)

            for key, btn in self.nav_buttons.items():
                btn.setChecked(key == page_name)

            self.lbl_topbar_title.setText(f"{page_name}")

            if changed:
                self._fade_in(widget)

            # Only refresh if forced or page is marked dirty
            if hasattr(widget, "refresh"):
                if force_refresh or getattr(widget, "_needs_refresh", True):
                    widget.refresh()
                    if hasattr(widget, "_needs_refresh"):
                        widget._needs_refresh = False

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

        # Mark Dashboard and History as dirty since scan results changed
        if hasattr(self.page_dashboard, "_needs_refresh"):
            self.page_dashboard._needs_refresh = True
        if hasattr(self.page_history, "_needs_refresh"):
            self.page_history._needs_refresh = True

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
        self.toasts.show(
            "Scan complete",
            f"{summary.get('processed', 0)} photos processed · {summary.get('matched', 0)} matched",
            "success",
        )

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

    # ------------------------------------------------------------------
    # Sidebar collapse / shortcuts / transitions / onboarding

    def _toggle_sidebar(self):
        self._sidebar_collapsed = not self._sidebar_collapsed
        self._apply_sidebar_collapsed(animate=True)

    def _apply_sidebar_collapsed(self, animate: bool = True):
        collapsed = self._sidebar_collapsed
        target_w = 64 if collapsed else 235

        for key, btn in self.nav_buttons.items():
            btn.setText("" if collapsed else self._nav_labels[key])
            btn.setStyleSheet("text-align: center;" if collapsed else "")

        # Title col must shrink to min when collapsed so the icon has room to center.
        # Force the col's max-size to its min when hidden; restore when shown.
        for lbl in (self.app_title, self.app_sub):
            lbl.setVisible(not collapsed)
        for lbl in self._section_labels:
            lbl.setVisible(not collapsed)

        # Collapse the title widget to free horizontal space so the icon can center.
        self._brand_text.setVisible(not collapsed)

        # Center the icon in collapsed mode by making the left/right stretches equal.
        self._header_top_row.setStretch(0, 1 if collapsed else 0)
        self._header_top_row.setStretch(3, 1)
        self._toggle_row.setStretch(0, 1)
        self._toggle_row.setStretch(2, 1 if collapsed else 0)

        if collapsed:
            self.lbl_sys_status.setText("●")
            self.lbl_hw_status.setVisible(False)
        else:
            self.lbl_hw_status.setVisible(True)
            self.update_hardware_status_badge()
            if not self.is_scanning_active:
                self.lbl_sys_status.setText("● System Ready")

        self.btn_sidebar_toggle.setIcon(
            get_icon("chevron_right" if collapsed else "chevron_left", color="#94a3b8", size=16)
        )
        self.btn_sidebar_toggle.setToolTip("Expand sidebar" if collapsed else "Collapse sidebar")

        sidebar = self.sidebar
        if animate:
            start_w = sidebar.width() or sidebar.minimumWidth()
            self._sidebar_anims = []
            for prop in (b"minimumWidth", b"maximumWidth"):
                anim = QPropertyAnimation(sidebar, prop, self)
                anim.setDuration(280)
                anim.setStartValue(start_w)
                anim.setEndValue(target_w)
                anim.setEasingCurve(QEasingCurve.InOutCubic)
                anim.start()
                self._sidebar_anims.append(anim)
        else:
            sidebar.setMinimumWidth(target_w)
            sidebar.setMaximumWidth(target_w)

    def _setup_shortcuts(self):
        bindings = [
            ("Ctrl+D", "Dashboard"),
            ("Ctrl+P", "People"),
            ("Ctrl+F", "Find Photos"),
            ("Ctrl+N", "New Scan"),
            ("Ctrl+Shift+N", "Solo Scan"),
            ("Ctrl+R", "Results"),
            ("Ctrl+U", "Unknown Faces"),
            ("Ctrl+H", "History"),
            ("Ctrl+,", "Settings"),
        ]
        self._shortcuts = []
        for seq, page_name in bindings:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(lambda p=page_name: self.navigate_to(p))
            self._shortcuts.append(sc)

        quit_sc = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_sc.activated.connect(self.close)
        esc_sc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc_sc.activated.connect(self._on_escape)
        self._shortcuts.extend([quit_sc, esc_sc])

    def _on_escape(self):
        """Escape cancels an in-flight scan (opens the processing page's confirm dialog)."""
        if self.is_scanning_active and self.content_stack.currentWidget() is self.page_processing:
            self.page_processing.btn_cancel.click()

    def _fade_in(self, widget: QWidget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            # Only clear if no newer effect replaced this one
            if widget.graphicsEffect() is effect:
                widget.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start()
        self._fade_anims[widget] = anim

    def _maybe_start_tour(self):
        if self.settings_service.get("ui.onboarding_done", False):
            return
        steps = [
            TourStep(
                "Welcome to Photo Face AI",
                "Organize thousands of photos automatically by the people in them. "
                "Start here — add people and reference photos, then run a scan.",
                lambda: self.nav_buttons.get("People"),
            ),
            TourStep(
                "Find Photos by Person",
                "After a scan, find all photos of any person in seconds. "
                "Search by name, filter by date or folder.",
                lambda: self.nav_buttons.get("Find Photos"),
            ),
            TourStep(
                "New Scan",
                "Point a scan at any photo folder. The AI detects every face and sorts "
                "photos into folders per person. (Ctrl+N)",
                lambda: self.nav_buttons.get("New Scan"),
            ),
            TourStep(
                "Results",
                "Review exactly how each photo was matched, fix mistakes inline, and "
                "reopen results any time from History.",
                lambda: self.nav_buttons.get("Results"),
            ),
        ]
        self._tour = OnboardingTour(self.centralWidget(), steps)
        self._tour.finished.connect(lambda: self.settings_service.set("ui.onboarding_done", True))
        self._tour.start()
