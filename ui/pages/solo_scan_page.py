"""
Solo Scan Wizard Page Module.

Dedicated 5-Step wizard for organizing single-person (solo) photos.
Strictly filters out group photos (2+ faces) and provides optional
Copy Mode vs Move Mode (Copy -> Verify -> Prompt Delete) settings.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from domain.scanner import discover_photos
from services.profile_service import ProfileService
from services.settings_service import SettingsService
from services.solo_scan_service import SoloScanService


class SoloScanPage(QWidget):
    """Wizard page for configuring and launching a dedicated Solo Photo organization scan."""

    def __init__(
        self,
        profile_service: ProfileService,
        solo_scan_service: SoloScanService,
        settings_service: SettingsService,
        on_scan_started_cb: Callable[[Any, dict[str, Any]], None],
    ):
        super().__init__()
        self.profile_service = profile_service
        self.solo_scan_service = solo_scan_service
        self.settings_service = settings_service
        self.on_scan_started_cb = on_scan_started_cb

        self.sources: list[str] = []
        self.selected_profile_ids: set[str] = set()
        self.output_dir_path: str = str(Path.home() / "Pictures" / "Organized_Solo_Photos")

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("👤 Solo Photo Scan Wizard")
        header.setProperty("class", "PageHeader")
        layout.addWidget(header)

        # Wizard Step Header Buttons
        self.steps_bar = QHBoxLayout()
        self.step_buttons = []
        step_names = ["1. Sources", "2. Profiles", "3. Output & Mode", "4. Performance", "5. Review"]

        for i, name in enumerate(step_names):
            btn = QPushButton(name)
            btn.setProperty("class", "NavButton")
            btn.setCheckable(True)
            btn.setEnabled(False)
            btn.clicked.connect(lambda _, idx=i: self.stacked_widget.setCurrentIndex(idx))
            self.steps_bar.addWidget(btn)
            self.step_buttons.append(btn)

        layout.addLayout(self.steps_bar)

        # Wizard Stacked Pages
        self.stacked_widget = QStackedWidget()

        # Step 1: Sources
        self.stacked_widget.addWidget(self._create_step1_sources())
        # Step 2: Profiles
        self.stacked_widget.addWidget(self._create_step2_profiles())
        # Step 3: Output Directory & Operation Mode
        self.stacked_widget.addWidget(self._create_step3_output())
        # Step 4: Performance Preferences
        self.stacked_widget.addWidget(self._create_step4_performance())
        # Step 5: Review & Start
        self.stacked_widget.addWidget(self._create_step5_review())

        layout.addWidget(self.stacked_widget)

        # Navigation Controls Footer
        nav_footer = QHBoxLayout()

        self.btn_prev = QPushButton("◀ Back")
        self.btn_prev.setProperty("class", "SecondaryButton")
        self.btn_prev.clicked.connect(self._go_prev)
        nav_footer.addWidget(self.btn_prev)

        nav_footer.addStretch()

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setProperty("class", "PrimaryButton")
        self.btn_next.clicked.connect(self._go_next)
        nav_footer.addWidget(self.btn_next)

        self.btn_start = QPushButton("🚀 Start Solo Scan")
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setStyleSheet("background-color: #10b981;")
        self.btn_start.clicked.connect(self._start_scan)
        self.btn_start.hide()
        nav_footer.addWidget(self.btn_start)

        layout.addLayout(nav_footer)

        self.stacked_widget.currentChanged.connect(self._on_step_changed)
        self._update_step_buttons(0)

    # STEP 1: SOURCES
    def _create_step1_sources(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)

        l.addWidget(QLabel("Select Photo Files or Directories to Scan for Solo Photos:"))

        btn_layout = QHBoxLayout()
        btn_add_folder = QPushButton("📁 Add Folder")
        btn_add_folder.setProperty("class", "SecondaryButton")
        btn_add_folder.clicked.connect(self._add_folder)

        btn_add_files = QPushButton("🖼️ Add Photo Files")
        btn_add_files.setProperty("class", "SecondaryButton")
        btn_add_files.clicked.connect(self._add_files)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.clicked.connect(self._clear_sources)

        btn_layout.addWidget(btn_add_folder)
        btn_layout.addWidget(btn_add_files)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        l.addLayout(btn_layout)

        self.chk_recursive = QCheckBox("Scan subdirectories recursively")
        self.chk_recursive.setChecked(self.settings_service.get("recursive_scan", True))
        self.chk_recursive.setStyleSheet("color: #ffffff;")
        l.addWidget(self.chk_recursive)

        self.sources_list = QListWidget()
        l.addWidget(self.sources_list)

        return widget

    # STEP 2: PROFILES
    def _create_step2_profiles(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)

        l.addWidget(QLabel("Select Person Profiles to Match (Individual Solo Matching Only):"))

        top_bar = QHBoxLayout()
        self.chk_select_all = QCheckBox("Select All Profiles")
        self.chk_select_all.setStyleSheet("color: #ffffff; font-weight: bold;")
        self.chk_select_all.toggled.connect(self._toggle_select_all_profiles)
        top_bar.addWidget(self.chk_select_all)
        top_bar.addStretch()
        l.addLayout(top_bar)

        self.profiles_list_widget = QListWidget()
        l.addWidget(self.profiles_list_widget)

        return widget

    # STEP 3: OUTPUT & OPERATION MODE
    def _create_step3_output(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)

        l.addWidget(QLabel("Destination Directory & Operation Mode:"))

        h = QHBoxLayout()
        self.output_dir_input = QPushButton("Select Output Folder...")
        self.output_dir_input.setProperty("class", "SecondaryButton")
        self.output_dir_input.clicked.connect(self._select_output_dir)

        self.lbl_selected_output = QLabel(self.output_dir_path)
        self.lbl_selected_output.setStyleSheet("font-size: 14px; font-weight: bold; color: #3b82f6;")

        h.addWidget(self.output_dir_input)
        h.addWidget(self.lbl_selected_output)
        h.addStretch()
        l.addLayout(h)

        # Operation Mode Options (Copy vs Move)
        mode_box = QFrame()
        mode_box.setStyleSheet("background-color: #1e1e24; border-radius: 8px; padding: 12px; margin-top: 12px;")
        mb_layout = QVBoxLayout(mode_box)

        mb_layout.addWidget(QLabel("File Operation Mode:"))

        self.rad_copy_mode = QRadioButton("📁 Copy Mode (Recommended): Copy photos to destination (Keep original source files)")
        self.rad_copy_mode.setChecked(True)
        self.rad_copy_mode.setStyleSheet("color: #ffffff; font-size: 13px;")
        mb_layout.addWidget(self.rad_copy_mode)

        self.rad_move_mode = QRadioButton("✂️ Move Mode (Copy → Verify 100% → Confirm Delete Original Files)")
        self.rad_move_mode.setStyleSheet("color: #ffffff; font-size: 13px;")
        mb_layout.addWidget(self.rad_move_mode)

        info_lbl = QLabel(
            "<i>Note on Move Mode: Photos are copied first. After the scan finishes and 100% of copies pass disk size verification, "
            "the application will ask for your final confirmation before removing verified source photos.</i>"
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px; margin-top: 4px;")
        mb_layout.addWidget(info_lbl)

        l.addWidget(mode_box)
        l.addStretch()
        return widget

    # STEP 4: PERFORMANCE
    def _create_step4_performance(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)

        l.addWidget(QLabel("Performance & Matching Preferences:"))

        l.addWidget(QLabel("Performance Mode:"))
        self.combo_perf = QComboBox()
        self.combo_perf.addItems(["Eco", "Balanced", "Maximum Performance"])
        self.combo_perf.setCurrentText(self.settings_service.get("performance_mode", "Maximum Performance"))
        l.addWidget(self.combo_perf)

        l.addWidget(QLabel("Matching Precision Threshold (Default 70 for High Precision & Zero False Matches):"))
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 100)
        self.spin_threshold.setValue(70)
        l.addWidget(self.spin_threshold)

        l.addStretch()
        return widget

    # STEP 5: REVIEW
    def _create_step5_review(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)

        l.addWidget(QLabel("Review Solo Scan Configuration:"))

        self.lbl_review_sources = QLabel()
        self.lbl_review_files = QLabel()
        self.lbl_review_profiles = QLabel()
        self.lbl_review_output = QLabel()
        self.lbl_review_mode = QLabel()
        self.lbl_review_settings = QLabel()

        for lbl in [
            self.lbl_review_sources,
            self.lbl_review_files,
            self.lbl_review_profiles,
            self.lbl_review_output,
            self.lbl_review_mode,
            self.lbl_review_settings,
        ]:
            lbl.setStyleSheet("font-size: 14px; margin-bottom: 6px; color: #ffffff;")
            l.addWidget(lbl)

        l.addStretch()
        return widget

    def reset_wizard(self):
        self.sources.clear()
        self.sources_list.clear()
        self.selected_profile_ids.clear()
        if hasattr(self, "chk_select_all"):
            self.chk_select_all.setChecked(True)
            self._toggle_select_all_profiles(True)
        if hasattr(self, "stacked_widget"):
            self.stacked_widget.setCurrentIndex(0)
            self._update_step_buttons(0)

    def refresh(self):
        self.reset_wizard()
        self.profiles_list_widget.clear()
        profiles = self.profile_service.list_profiles()
        for p in profiles:
            if not p.get("is_group_profile"):
                item = QListWidgetItem(p["name"])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setData(Qt.UserRole, p["id"])
                self.profiles_list_widget.addItem(item)
        self.chk_select_all.setChecked(True)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder for Solo Scan")
        if folder and folder not in self.sources:
            self.sources.append(folder)
            self.sources_list.addItem(folder)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Image Files", "", "Images (*.jpg *.jpeg *.png *.webp *.heic *.tif *.tiff)")
        for f in files:
            if f not in self.sources:
                self.sources.append(f)
                self.sources_list.addItem(f)

    def _clear_sources(self):
        self.sources.clear()
        self.sources_list.clear()

    def _toggle_select_all_profiles(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.profiles_list_widget.count()):
            self.profiles_list_widget.item(i).setCheckState(state)

    def _select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory for Solo Photos")
        if folder:
            self.output_dir_path = folder
            self.lbl_selected_output.setText(folder)

    def _on_step_changed(self, idx: int):
        self._update_step_buttons(idx)

    def _update_step_buttons(self, idx: int):
        for i, btn in enumerate(self.step_buttons):
            btn.setChecked(i == idx)

        self.btn_prev.setEnabled(idx > 0)
        if idx == 4:  # Review Step
            self.btn_next.hide()
            self.btn_start.show()
            self._populate_review()
        else:
            self.btn_next.show()
            self.btn_start.hide()

    def _populate_review(self):
        self.lbl_review_sources.setText(f"• Sources: {len(self.sources)} folder/file paths")
        try:
            discovered = discover_photos(self.sources, recursive=self.chk_recursive.isChecked())
        except Exception:
            discovered = []
        self.lbl_review_files.setText(f"• Estimated Photos: {len(discovered)} images found")

        sel_p_names = []
        self.selected_profile_ids.clear()
        for i in range(self.profiles_list_widget.count()):
            item = self.profiles_list_widget.item(i)
            if item and item.checkState() == Qt.Checked:
                sel_p_names.append(item.text())
                self.selected_profile_ids.add(item.data(Qt.UserRole))

        out_path = getattr(self, "output_dir_path", "Not Selected")
        op_mode = "Move Mode (Copy → Verify → Confirm Delete)" if self.rad_move_mode.isChecked() else "Copy Mode (Keep Originals)"

        self.lbl_review_profiles.setText(f"• Target Solo Profiles ({len(sel_p_names)}): {', '.join(sel_p_names) if sel_p_names else 'None'}")
        self.lbl_review_output.setText(f"• Output Folder: {out_path}")
        self.lbl_review_mode.setText(f"• File Operation: {op_mode}")
        self.lbl_review_settings.setText(
            f"• Mode: {self.combo_perf.currentText()} | Threshold: {self.spin_threshold.value()}"
        )

    def _go_next(self):
        curr = self.stacked_widget.currentIndex()
        if curr == 0 and not self.sources:
            QMessageBox.warning(self, "Validation Error", "Please select at least one source file or folder to scan.")
            return
        if curr == 1:
            sel_count = sum(
                1 for i in range(self.profiles_list_widget.count())
                if self.profiles_list_widget.item(i) and self.profiles_list_widget.item(i).checkState() == Qt.Checked
            )
            if sel_count == 0:
                QMessageBox.warning(self, "Validation Error", "Please select at least one profile to match against.")
                return
        if curr == 2 and not getattr(self, "output_dir_path", None):
            QMessageBox.warning(self, "Validation Error", "Please select an output directory.")
            return

        if curr < 4:
            self.stacked_widget.setCurrentIndex(curr + 1)

    def _go_prev(self):
        curr = self.stacked_widget.currentIndex()
        if curr > 0:
            self.stacked_widget.setCurrentIndex(curr - 1)

    def _start_scan(self):
        if not getattr(self, "output_dir_path", None):
            QMessageBox.warning(self, "Validation Error", "Please select an output directory.")
            return

        out_p = Path(self.output_dir_path)
        try:
            out_p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "Output Directory Error", f"Could not create output directory:\n{e}")
            return

        op_mode = "move" if self.rad_move_mode.isChecked() else "copy"

        worker, scan_meta = self.solo_scan_service.start_solo_scan(
            sources=self.sources,
            profile_ids=list(self.selected_profile_ids),
            output_dir=self.output_dir_path,
            recursive=self.chk_recursive.isChecked(),
            performance_mode=self.combo_perf.currentText(),
            operation_mode=op_mode,
            threshold=float(self.spin_threshold.value()),
        )

        self.on_scan_started_cb(worker, scan_meta)
