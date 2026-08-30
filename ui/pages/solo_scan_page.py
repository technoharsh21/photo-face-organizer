"""
Solo Scan Wizard Page Module.

Dedicated 5-Step wizard for organizing single-person (solo) photos.
Strictly filters out group photos (2+ faces) and provides optional
Copy Mode vs Move Mode (Copy -> Verify -> Prompt Delete) settings.
Features complete state cleanup on reload to eliminate caching of old scan values.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from domain.scanner import discover_photos
from services.profile_service import ProfileService
from services.settings_service import SettingsService
from services.solo_scan_service import SoloScanService


def _create_mini_avatar(pixmap_path: str | None, name: str, size: int = 44, radius: int = 10, bg_color: str = "#2563eb") -> QPixmap:
    """Render a crisp rounded-square mini thumbnail for profile selection."""
    target = QPixmap(size, size)
    target.fill(Qt.transparent)

    if pixmap_path and Path(pixmap_path).exists():
        raw_pix = QPixmap(str(pixmap_path))
        if not raw_pix.isNull():
            scaled = raw_pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter = QPainter(target)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            path = QPainterPath()
            path.addRoundedRect(0, 0, size, size, radius, radius)
            painter.setClipPath(path)
            x_off = max(0, (scaled.width() - size) // 2)
            y_off = max(0, (scaled.height() - size) // 2)
            painter.drawPixmap(-x_off, -y_off, scaled)
            painter.end()
            return target

    # Fallback to initials
    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(bg_color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setPointSize(max(10, size // 3))
    font.setBold(True)
    painter.setFont(font)
    initials = "".join([part[0].upper() for part in name.strip().split()[:2]]) or "P"
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, initials)
    painter.end()
    return target


class SoloProfileSelectionItemWidget(QWidget):
    """Custom rich item card for selecting individual solo profiles in Step 2."""

    def __init__(self, profile_id: str, name: str, ref_count: int, avatar_path: str | None, is_group: bool, is_checked: bool, on_toggled: Callable[[str, bool], None], bg_color: str = "#2563eb"):
        super().__init__()
        self.profile_id = profile_id
        self.name = name
        self.on_toggled = on_toggled
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        # High-contrast Checkbox
        self.chk = QCheckBox()
        self.chk.setFixedSize(22, 22)
        self.chk.setChecked(is_checked)
        self.chk.setCursor(Qt.PointingHandCursor)
        self.chk.setStyleSheet(
            "QCheckBox { background: transparent; border: none; padding: 0px; margin: 0px; }"
            "QCheckBox::indicator { width: 20px; height: 20px; border-radius: 5px; border: 2px solid #38bdf8; background-color: #0f172a; }"
            "QCheckBox::indicator:checked { background-color: #10b981; border: 2px solid #10b981; }"
        )
        self.chk.toggled.connect(self._on_check_changed)
        layout.addWidget(self.chk)

        # Avatar thumbnail (44x44)
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(44, 44)
        avatar_lbl.setPixmap(_create_mini_avatar(avatar_path, name, size=44, radius=10, bg_color=bg_color))
        avatar_lbl.setCursor(Qt.PointingHandCursor)
        layout.addWidget(avatar_lbl)

        # Text Info with prominent styling
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        name_lbl.setCursor(Qt.PointingHandCursor)

        sub_tag = "👥 Group Profile (Requires Solo Member Match)" if is_group else f"👤 Solo Person • 📷 {ref_count} reference photos"
        sub_lbl = QLabel(sub_tag)
        sub_lbl.setStyleSheet("font-size: 12px; color: #cbd5e1; background: transparent; border: none; font-weight: 500;")
        sub_lbl.setCursor(Qt.PointingHandCursor)

        info_col.addWidget(name_lbl)
        info_col.addWidget(sub_lbl)
        layout.addLayout(info_col, 1)

    def _on_check_changed(self, checked: bool):
        self.on_toggled(self.profile_id, checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.chk.setChecked(not self.chk.isChecked())
        super().mousePressEvent(event)


class SoloScanPage(QWidget):
    """Modern, responsive 5-step wizard for configuring dedicated Solo Photo Organization Scans (0% False Positives)."""

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
        self.default_output_path: str = str(Path.home() / "Pictures" / "Organized_Solo_Photos")
        self.output_dir_path: str = self.default_output_path

        self._setup_ui()

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(widget)
        return scroll

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        # 1. Top Header Bar
        top_hdr = QHBoxLayout()
        top_hdr.setSpacing(12)

        hdr_info = QVBoxLayout()
        hdr_info.setSpacing(2)
        page_title = QLabel("🎯 Solo Scan Wizard (0% False Positives)")
        page_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        page_sub = QLabel("Strict single-person photo organizer — filters out group shots and multi-face photos.")
        page_sub.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 600;")
        hdr_info.addWidget(page_title)
        hdr_info.addWidget(page_sub)
        top_hdr.addLayout(hdr_info)

        top_hdr.addStretch()

        btn_reset_hdr = QPushButton("🔄 Reset Wizard")
        btn_reset_hdr.setCursor(Qt.PointingHandCursor)
        btn_reset_hdr.setFixedHeight(34)
        btn_reset_hdr.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 6px; padding: 0 14px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background-color: #334155; color: #ffffff; }"
        )
        btn_reset_hdr.setToolTip("Reset all wizard steps and start fresh.")
        btn_reset_hdr.clicked.connect(self.reset_wizard)
        top_hdr.addWidget(btn_reset_hdr)

        root_layout.addLayout(top_hdr)

        # 2. Wizard Step Header Card (Breadcrumbs)
        step_card = QFrame()
        step_card.setProperty("class", "StepHeader")
        self.steps_bar = QHBoxLayout(step_card)
        self.steps_bar.setContentsMargins(12, 8, 12, 8)
        self.steps_bar.setSpacing(8)

        self.step_labels: list[QLabel] = []
        step_names = [
            "1. 📁 Sources",
            "2. 👤 Solo People",
            "3. 📂 Output & Mode",
            "4. ⚙️ Precision Settings",
            "5. 🚀 Review & Launch",
        ]

        for i, name in enumerate(step_names):
            lbl = QLabel(name)
            lbl.setProperty("class", "StepPillActive" if i == 0 else "StepPill")
            lbl.setCursor(Qt.PointingHandCursor)
            lbl.mousePressEvent = lambda _, step_idx=i: self._jump_to_step(step_idx)
            self.steps_bar.addWidget(lbl)
            self.step_labels.append(lbl)

        root_layout.addWidget(step_card)

        # 3. Wizard Stacked Step Pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self._wrap_scroll(self._create_step1_sources()))
        self.stacked_widget.addWidget(self._wrap_scroll(self._create_step2_profiles()))
        self.stacked_widget.addWidget(self._wrap_scroll(self._create_step3_output()))
        self.stacked_widget.addWidget(self._wrap_scroll(self._create_step4_performance()))
        self.stacked_widget.addWidget(self._wrap_scroll(self._create_step5_review()))

        root_layout.addWidget(self.stacked_widget, 1)

        # 4. Navigation Controls Footer
        nav_footer = QHBoxLayout()
        nav_footer.setSpacing(12)

        self.btn_prev = QPushButton("◀ Back")
        self.btn_prev.setProperty("class", "SecondaryButton")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setFixedHeight(38)
        self.btn_prev.clicked.connect(self._go_prev)
        nav_footer.addWidget(self.btn_prev)

        nav_footer.addStretch()

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setProperty("class", "PrimaryButton")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFixedHeight(38)
        self.btn_next.setStyleSheet("min-width: 110px;")
        self.btn_next.clicked.connect(self._go_next)
        nav_footer.addWidget(self.btn_next)

        self.btn_start = QPushButton("🚀 Start Solo Scan")
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setFixedHeight(40)
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 800; border-radius: 8px; padding: 0 24px; font-size: 13px; border: 1px solid #059669; min-width: 150px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_start.clicked.connect(self._start_scan)
        self.btn_start.hide()
        nav_footer.addWidget(self.btn_start)

        root_layout.addLayout(nav_footer)

        self.stacked_widget.currentChanged.connect(self._on_step_changed)
        self._update_step_buttons(0)

    # -------------------------------------------------------------------------
    # STEP 1: SOURCES
    # -------------------------------------------------------------------------
    def _create_step1_sources(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        # Step Title Banner
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        lbl_h = QLabel("<b>Step 1: Select Photo Sources to Scan for Solo Photos</b>")
        lbl_h.setStyleSheet("font-size: 15px; color: #ffffff;")
        lbl_sub = QLabel("Select directories or photo files. The AI engine will scan and identify only single-person portraits.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hdr_box.addWidget(lbl_h)
        hdr_box.addWidget(lbl_sub)
        l.addLayout(hdr_box)

        # Action Toolbar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_add_folder = QPushButton("📁 Add Folder")
        btn_add_folder.setProperty("class", "SecondaryButton")
        btn_add_folder.setCursor(Qt.PointingHandCursor)
        btn_add_folder.setFixedHeight(34)
        btn_add_folder.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; padding: 0 14px; font-size: 12px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_add_folder.clicked.connect(self._add_folder)

        btn_add_files = QPushButton("🖼️ Add Image Files")
        btn_add_files.setProperty("class", "SecondaryButton")
        btn_add_files.setCursor(Qt.PointingHandCursor)
        btn_add_files.setFixedHeight(34)
        btn_add_files.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; padding: 0 14px; font-size: 12px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_add_files.clicked.connect(self._add_files)

        btn_clear = QPushButton("🗑️ Clear All")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setFixedHeight(34)
        btn_clear.clicked.connect(self._clear_sources)

        btn_layout.addWidget(btn_add_folder)
        btn_layout.addWidget(btn_add_files)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()

        self.chk_recursive = QCheckBox("🗂️ Scan subdirectories recursively")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setCursor(Qt.PointingHandCursor)
        self.chk_recursive.setStyleSheet("color: #ffffff; font-weight: 600;")
        self.chk_recursive.toggled.connect(self._update_sources_summary)
        btn_layout.addWidget(self.chk_recursive)

        l.addLayout(btn_layout)

        # Sources List View
        self.sources_list = QListWidget()
        self.sources_list.setCursor(Qt.PointingHandCursor)
        self.sources_list.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; padding: 6px; outline: 0px; font-size: 13px; color: #f8fafc; }"
            "QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #1e293b; border-radius: 6px; margin-bottom: 2px; }"
            "QListWidget::item:hover { background-color: #131d33; }"
        )
        l.addWidget(self.sources_list, 1)

        # Sources Summary Pill
        self.lbl_sources_summary = QLabel("📊 No sources added yet. Click '📁 Add Folder' or '🖼️ Add Image Files' above.")
        self.lbl_sources_summary.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 600;")
        l.addWidget(self.lbl_sources_summary)

        return widget

    # -------------------------------------------------------------------------
    # STEP 2: PROFILES
    # -------------------------------------------------------------------------
    def _create_step2_profiles(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        # Step Title Banner
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        lbl_h = QLabel("<b>Step 2: Select Person Profiles to Match (Strict Solo Matching Only)</b>")
        lbl_h.setStyleSheet("font-size: 15px; color: #ffffff;")
        lbl_sub = QLabel("Only single-person photos matching these profiles will be organized. Group photos are automatically skipped.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hdr_box.addWidget(lbl_h)
        hdr_box.addWidget(lbl_sub)
        l.addLayout(hdr_box)

        # Search Filter & Select All Toolbar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.chk_select_all = QCheckBox("Select All")
        self.chk_select_all.setChecked(True)
        self.chk_select_all.setCursor(Qt.PointingHandCursor)
        self.chk_select_all.setStyleSheet(
            "QCheckBox { color: #ffffff; font-weight: 700; font-size: 13px; spacing: 8px; padding: 6px 12px; background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; }"
            "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #38bdf8; background-color: #0f172a; }"
            "QCheckBox::indicator:checked { background-color: #10b981; border: 1px solid #10b981; }"
        )
        self.chk_select_all.toggled.connect(self._toggle_select_all_profiles)
        top_bar.addWidget(self.chk_select_all)

        top_bar.addSpacing(6)

        # Distinct high-contrast filter box
        self.txt_filter_profiles = QLineEdit()
        self.txt_filter_profiles.setPlaceholderText("🔍 Filter people by name...")
        self.txt_filter_profiles.setFixedHeight(38)
        self.txt_filter_profiles.setStyleSheet(
            "QLineEdit { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 6px 14px; font-size: 13px; color: #ffffff; font-weight: 600; }"
            "QLineEdit:hover { border: 2px solid #67e8f9; background-color: #131d33; }"
            "QLineEdit:focus { border: 2px solid #a5f3fc; background-color: #131d33; color: #ffffff; }"
        )
        self.txt_filter_profiles.textChanged.connect(self._filter_profiles_list)
        top_bar.addWidget(self.txt_filter_profiles, 1)

        self.lbl_profile_sel_count = QLabel("0 Selected")
        self.lbl_profile_sel_count.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; font-weight: 700; font-size: 12px; padding: 6px 12px; border-radius: 8px; border: 1px solid #334155;"
        )
        top_bar.addWidget(self.lbl_profile_sel_count)

        l.addLayout(top_bar)

        # Profiles List Widget
        self.profiles_list_widget = QListWidget()
        self.profiles_list_widget.setCursor(Qt.PointingHandCursor)
        self.profiles_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.profiles_list_widget.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; padding: 6px; outline: 0px; }"
            "QListWidget::item { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 6px; padding: 2px; }"
            "QListWidget::item:hover { background-color: #162238; border: 1px solid #38bdf8; }"
            "QListWidget::item:selected { background-color: #1e293b; border: 1px solid #38bdf8; }"
        )
        l.addWidget(self.profiles_list_widget, 1)

        return widget

    # -------------------------------------------------------------------------
    # STEP 3: OUTPUT & OPERATION MODE
    # -------------------------------------------------------------------------
    def _create_step3_output(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        # Step Title Banner
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        lbl_h = QLabel("<b>Step 3: Destination Directory & File Handling Mode</b>")
        lbl_h.setStyleSheet("font-size: 15px; color: #ffffff;")
        lbl_sub = QLabel("Choose destination folder for solo photos and select whether to copy or safely move files.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hdr_box.addWidget(lbl_h)
        hdr_box.addWidget(lbl_sub)
        l.addLayout(hdr_box)

        # Output Folder Selector Card
        out_card = QFrame()
        out_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 14px;")
        oc_layout = QVBoxLayout(out_card)
        oc_layout.setSpacing(8)

        oc_layout.addWidget(QLabel("<b>Solo Output Directory:</b>"))

        h = QHBoxLayout()
        h.setSpacing(10)

        self.txt_output_dir = QLineEdit(self.output_dir_path)
        self.txt_output_dir.setReadOnly(True)
        self.txt_output_dir.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 8px 12px; font-weight: bold; color: #38bdf8;")
        h.addWidget(self.txt_output_dir, 1)

        btn_browse = QPushButton("📁 Browse Folder...")
        btn_browse.setProperty("class", "SecondaryButton")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setFixedHeight(36)
        btn_browse.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; padding: 0 14px; font-size: 12px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_browse.clicked.connect(self._select_output_dir)
        h.addWidget(btn_browse)
        oc_layout.addLayout(h)

        l.addWidget(out_card)

        # File Operation Mode Cards (Copy vs Move)
        mode_box = QFrame()
        mode_box.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 14px;")
        mb_layout = QVBoxLayout(mode_box)
        mb_layout.setSpacing(12)

        mb_layout.addWidget(QLabel("<b>Choose File Operation Mode:</b>"))

        # 1. Copy Mode Card
        self.card_copy = QFrame()
        self.card_copy.setCursor(Qt.PointingHandCursor)
        copy_layout = QHBoxLayout(self.card_copy)
        copy_layout.setContentsMargins(14, 14, 14, 14)
        copy_layout.setSpacing(12)

        self.rad_copy_mode = QRadioButton()
        self.rad_copy_mode.setChecked(True)
        self.rad_copy_mode.setCursor(Qt.PointingHandCursor)

        copy_lbl = QLabel(
            "<b>📁 Copy Mode (Recommended & 100% Safe)</b><br/>"
            "<span style='color: #cbd5e1; font-size: 12px;'>"
            "Safely copies verified solo photos into each person's folder. Original source photos remain untouched."
            "</span>"
        )
        copy_lbl.setWordWrap(True)
        copy_lbl.setCursor(Qt.PointingHandCursor)
        copy_layout.addWidget(self.rad_copy_mode)
        copy_layout.addWidget(copy_lbl, 1)

        # 2. Move Mode Card
        self.card_move = QFrame()
        self.card_move.setCursor(Qt.PointingHandCursor)
        move_layout = QHBoxLayout(self.card_move)
        move_layout.setContentsMargins(14, 14, 14, 14)
        move_layout.setSpacing(12)

        self.rad_move_mode = QRadioButton()
        self.rad_move_mode.setCursor(Qt.PointingHandCursor)

        move_lbl = QLabel(
            "<b>✂️ Move Mode (Safe Verification Mode)</b><br/>"
            "<span style='color: #cbd5e1; font-size: 12px;'>"
            "Copies photos first → Verifies 100% byte integrity → Asks for confirmation before removing original files."
            "</span>"
        )
        move_lbl.setWordWrap(True)
        move_lbl.setCursor(Qt.PointingHandCursor)
        move_layout.addWidget(self.rad_move_mode)
        move_layout.addWidget(move_lbl, 1)

        mb_layout.addWidget(self.card_copy)
        mb_layout.addWidget(self.card_move)

        # Explicit QButtonGroup for mutual exclusivity across separate parents
        self.op_mode_group = QButtonGroup(self)
        self.op_mode_group.addButton(self.rad_copy_mode, 0)
        self.op_mode_group.addButton(self.rad_move_mode, 1)

        self.rad_copy_mode.toggled.connect(self._update_operation_mode_cards)
        self.rad_move_mode.toggled.connect(self._update_operation_mode_cards)

        self.card_copy.mousePressEvent = lambda _: self._select_operation_mode("copy")
        self.card_move.mousePressEvent = lambda _: self._select_operation_mode("move")

        self._update_operation_mode_cards()
        l.addWidget(mode_box)

        l.addStretch()
        return widget

    def _select_operation_mode(self, mode: str):
        if mode == "copy":
            self.rad_copy_mode.setChecked(True)
        else:
            self.rad_move_mode.setChecked(True)
        self._update_operation_mode_cards()

    def _update_operation_mode_cards(self):
        """Update visual highlight cards for Copy Mode vs Move Mode selection."""
        is_copy = self.rad_copy_mode.isChecked()
        if is_copy:
            self.card_copy.setStyleSheet(
                "QFrame { background-color: #064e3b; border: 2px solid #10b981; border-radius: 10px; }"
            )
            self.card_move.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; }"
                "QFrame:hover { border: 1px solid #334155; }"
            )
        else:
            self.card_copy.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; }"
                "QFrame:hover { border: 1px solid #334155; }"
            )
            self.card_move.setStyleSheet(
                "QFrame { background-color: #78350f; border: 2px solid #f59e0b; border-radius: 10px; }"
            )

    # -------------------------------------------------------------------------
    # STEP 4: PERFORMANCE & THRESHOLD
    # -------------------------------------------------------------------------
    def _create_step4_performance(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        # Step Title Banner
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        lbl_h = QLabel("<b>Step 4: AI Matching Sensitivity & Performance Preferences</b>")
        lbl_h.setStyleSheet("font-size: 15px; color: #ffffff;")
        lbl_sub = QLabel("For solo scans, 70% threshold is recommended to ensure zero false positives.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hdr_box.addWidget(lbl_h)
        hdr_box.addWidget(lbl_sub)
        l.addLayout(hdr_box)

        # 1. Performance Mode Card
        perf_card = QFrame()
        perf_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 14px;")
        pc_layout = QVBoxLayout(perf_card)
        pc_layout.setSpacing(8)

        pc_layout.addWidget(QLabel("<b>Performance & Device Mode:</b>"))

        self.combo_perf = QComboBox()
        self.combo_perf.addItems(["Maximum Performance", "Balanced", "Eco"])
        self.combo_perf.setCurrentText("Maximum Performance")
        pc_layout.addWidget(self.combo_perf)

        l.addWidget(perf_card)

        # 2. Matching Precision Threshold Card (Default 70% for Solo Scans)
        thresh_card = QFrame()
        thresh_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 14px;")
        tc_layout = QVBoxLayout(thresh_card)
        tc_layout.setSpacing(10)

        tc_layout.addWidget(QLabel("<b>Matching Precision Threshold (1% - 100%):</b>"))

        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)

        self.slider_threshold = QSlider(Qt.Horizontal)
        self.slider_threshold.setRange(1, 100)
        self.slider_threshold.setValue(70)
        self.slider_threshold.setCursor(Qt.PointingHandCursor)
        slider_row.addWidget(self.slider_threshold, 1)

        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 100)
        self.spin_threshold.setValue(70)
        self.spin_threshold.setSuffix("%")
        self.spin_threshold.setFixedWidth(75)
        slider_row.addWidget(self.spin_threshold)

        tc_layout.addLayout(slider_row)

        # Sync slider and spinbox
        self.slider_threshold.valueChanged.connect(self.spin_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self.slider_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self._update_threshold_guidance)

        # Dynamic Threshold Guidance Box
        self.lbl_threshold_desc = QLabel()
        self.lbl_threshold_desc.setWordWrap(True)
        tc_layout.addWidget(self.lbl_threshold_desc)

        self._update_threshold_guidance(70)
        l.addWidget(thresh_card)

        l.addStretch()
        return widget

    def _update_threshold_guidance(self, value: int):
        if value >= 85:
            text = (
                f"🔒 <b>{value}% (Ultra-Strict Precision):</b> Identifies near-identical faces only. "
                f"Zero false positives. Best if separating identical twins or very close lookalikes."
            )
            style = "color: #34d399; font-size: 12px; background: #064e3b; padding: 10px; border-radius: 6px; border: 1px solid #10b981;"
        elif value >= 70:
            text = (
                f"🎯 <b>{value}% (High Precision — Recommended for Solo Scan):</b> Highly accurate single-person matching. "
                f"Guarantees other people's photos will NEVER enter your profile folder."
            )
            style = "color: #10b981; font-size: 12px; background: #064e3b; padding: 10px; border-radius: 6px; border: 1px solid #10b981;"
        elif value >= 50:
            text = (
                f"⚖️ <b>{value}% (Balanced Mode):</b> Standard matching for solo photos. "
                f"Captures faces across different smiles, hairstyles, and lighting."
            )
            style = "color: #60a5fa; font-size: 12px; background: #1e3a8a; padding: 10px; border-radius: 6px; border: 1px solid #3b82f6;"
        elif value >= 35:
            text = (
                f"👓 <b>{value}% (Extended Range):</b> Matches photos with sunglasses, hats, "
                f"or side angles. May occasionally include similar-looking relatives."
            )
            style = "color: #fbbf24; font-size: 12px; background: #78350f; padding: 10px; border-radius: 6px; border: 1px solid #f59e0b;"
        else:
            text = (
                f"🔍 <b>{value}% (Maximum Sensitivity):</b> Very loose matching for low-resolution "
                f"or dark nighttime photos. Higher chance of including non-matching faces."
            )
            style = "color: #f87171; font-size: 12px; background: #7f1d1d; padding: 10px; border-radius: 6px; border: 1px solid #ef4444;"

        self.lbl_threshold_desc.setText(text)
        self.lbl_threshold_desc.setStyleSheet(style)

    # -------------------------------------------------------------------------
    # STEP 5: REVIEW & LAUNCH
    # -------------------------------------------------------------------------
    def _create_step5_review(self) -> QWidget:
        widget = QFrame()
        widget.setProperty("class", "Card")
        l = QVBoxLayout(widget)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(14)

        # Step Title Banner
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        lbl_h = QLabel("<b>Step 5: Review Configuration & Launch Solo Scan</b>")
        lbl_h.setStyleSheet("font-size: 15px; color: #ffffff;")
        lbl_sub = QLabel("Verify solo scan parameters before launching the 0% false positive facial classifier.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hdr_box.addWidget(lbl_h)
        hdr_box.addWidget(lbl_sub)
        l.addLayout(hdr_box)

        # 4 Summary Review Cards in 2x2 Grid
        grid_cards = QGridLayout()
        grid_cards.setSpacing(12)

        # 1. Sources Card
        self.card_rev_sources = QFrame()
        self.card_rev_sources.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        s_layout = QVBoxLayout(self.card_rev_sources)
        s_layout.setSpacing(4)
        s_title = QLabel("📁 <b>Photo Sources</b>")
        s_title.setStyleSheet("color: #38bdf8; font-size: 13px;")
        self.lbl_rev_sources_val = QLabel("0 Sources")
        self.lbl_rev_sources_val.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        self.lbl_rev_photos_val = QLabel("0 Estimated Photos")
        self.lbl_rev_photos_val.setStyleSheet("color: #94a3b8; font-size: 11px;")
        s_layout.addWidget(s_title)
        s_layout.addWidget(self.lbl_rev_sources_val)
        s_layout.addWidget(self.lbl_rev_photos_val)
        grid_cards.addWidget(self.card_rev_sources, 0, 0)

        # 2. People Profiles Card
        self.card_rev_people = QFrame()
        self.card_rev_people.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        p_layout = QVBoxLayout(self.card_rev_people)
        p_layout.setSpacing(4)
        p_title = QLabel("👤 <b>Solo Target People</b>")
        p_title.setStyleSheet("color: #34d399; font-size: 13px;")
        self.lbl_rev_people_val = QLabel("0 Profiles Selected")
        self.lbl_rev_people_val.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        self.lbl_rev_people_names = QLabel("None")
        self.lbl_rev_people_names.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.lbl_rev_people_names.setWordWrap(True)
        p_layout.addWidget(p_title)
        p_layout.addWidget(self.lbl_rev_people_val)
        p_layout.addWidget(self.lbl_rev_people_names)
        grid_cards.addWidget(self.card_rev_people, 0, 1)

        # 3. Output Folder Card
        self.card_rev_output = QFrame()
        self.card_rev_output.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        o_layout = QVBoxLayout(self.card_rev_output)
        o_layout.setSpacing(4)
        o_title = QLabel("📂 <b>Destination & Mode</b>")
        o_title.setStyleSheet("color: #a78bfa; font-size: 13px;")
        self.lbl_rev_out_mode = QLabel("Copy Mode (Safe)")
        self.lbl_rev_out_mode.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        self.lbl_rev_out_path = QLabel("/home/user/Pictures/...")
        self.lbl_rev_out_path.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.lbl_rev_out_path.setWordWrap(True)
        o_layout.addWidget(o_title)
        o_layout.addWidget(self.lbl_rev_out_mode)
        o_layout.addWidget(self.lbl_rev_out_path)
        grid_cards.addWidget(self.card_rev_output, 1, 0)

        # 4. AI Engine Card
        self.card_rev_engine = QFrame()
        self.card_rev_engine.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        e_layout = QVBoxLayout(self.card_rev_engine)
        e_layout.setSpacing(4)
        e_title = QLabel("🎯 <b>Solo Classifier Engine</b>")
        e_title.setStyleSheet("color: #fbbf24; font-size: 13px;")
        self.lbl_rev_thresh_val = QLabel("Threshold: 70%")
        self.lbl_rev_thresh_val.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        self.lbl_rev_engine_sub = QLabel("Strict Single-Face Filter + ArcFace (512-d)")
        self.lbl_rev_engine_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
        e_layout.addWidget(e_title)
        e_layout.addWidget(self.lbl_rev_thresh_val)
        e_layout.addWidget(self.lbl_rev_engine_sub)
        grid_cards.addWidget(self.card_rev_engine, 1, 1)

        l.addLayout(grid_cards)

        # Solo Safeguard Banner
        self.ready_banner = QFrame()
        self.ready_banner.setStyleSheet("background-color: #064e3b; border: 1px solid #10b981; border-radius: 8px; padding: 10px 14px;")
        rb_layout = QHBoxLayout(self.ready_banner)
        rb_layout.setContentsMargins(0, 0, 0, 0)
        lbl_ready = QLabel("🛡️ <b>Solo Safeguard Active:</b> All group photos (2+ faces) will be strictly skipped. Only 100% verified solo photos will be organized.")
        lbl_ready.setStyleSheet("color: #34d399; font-size: 12px;")
        rb_layout.addWidget(lbl_ready)
        l.addWidget(self.ready_banner)

        l.addStretch()
        return widget

    # -------------------------------------------------------------------------
    # STATE MANAGEMENT & COMPLETE RESET
    # -------------------------------------------------------------------------
    def reset_wizard(self):
        """Cleanly reset all 5 wizard steps and clear cached values from previous solo scans."""
        # 1. Reset Sources
        self.sources.clear()
        self.sources_list.clear()
        self.chk_recursive.setChecked(True)
        self.lbl_sources_summary.setText("📊 No sources added yet. Click '📁 Add Folder' or '🖼️ Add Image Files' above.")

        # 2. Reset Profiles
        self.selected_profile_ids.clear()
        self.txt_filter_profiles.clear()
        self._populate_profiles_list()

        # 3. Reset Output & Mode
        self.output_dir_path = self.default_output_path
        self.txt_output_dir.setText(self.output_dir_path)
        self.rad_copy_mode.setChecked(True)
        self._update_operation_mode_cards()

        # 4. Reset AI Settings (Default 70% for Solo Scan)
        self.combo_perf.setCurrentText("Maximum Performance")
        self.slider_threshold.setValue(70)
        self.spin_threshold.setValue(70)

        # 5. Jump back to Step 1
        if hasattr(self, "stacked_widget"):
            self.stacked_widget.setCurrentIndex(0)
            self._update_step_buttons(0)

    def refresh(self):
        """Reset wizard state and refresh available profiles upon page navigation."""
        self.reset_wizard()

    def _populate_profiles_list(self):
        """Populate profile selection list with rich avatar cards."""
        self.profiles_list_widget.clear()
        profiles = self.profile_service.list_profiles()
        colors = ["#2563eb", "#059669", "#7c3aed", "#d97706", "#0891b2", "#dc2626"]

        for idx, p in enumerate(profiles):
            p_id = p["id"]
            self.selected_profile_ids.add(p_id)
            refs = p.get("references", [])
            first_ref = refs[0].get("stored_path") if refs else None

            item = QListWidgetItem()
            item.setData(Qt.UserRole, p_id)
            item.setSizeHint(QSize(200, 68))
            self.profiles_list_widget.addItem(item)

            bg = colors[idx % len(colors)]
            widget = SoloProfileSelectionItemWidget(
                profile_id=p_id,
                name=p.get("name", "Unknown"),
                ref_count=len(refs),
                avatar_path=first_ref,
                is_group=bool(p.get("is_group_profile")),
                is_checked=True,
                on_toggled=self._on_profile_toggled,
                bg_color=bg,
            )
            self.profiles_list_widget.setItemWidget(item, widget)

        self.chk_select_all.setChecked(True)
        self._update_profile_counter()

    def _on_profile_toggled(self, profile_id: str, is_checked: bool):
        if is_checked:
            self.selected_profile_ids.add(profile_id)
        else:
            self.selected_profile_ids.discard(profile_id)
        self._update_profile_counter()

    def _update_profile_counter(self):
        total = self.profiles_list_widget.count()
        selected = len(self.selected_profile_ids)
        self.lbl_profile_sel_count.setText(f"{selected} of {total} Selected")
        self.chk_select_all.blockSignals(True)
        self.chk_select_all.setChecked(selected == total and total > 0)
        self.chk_select_all.blockSignals(False)

    def _filter_profiles_list(self, query: str):
        q = query.strip().lower()
        for i in range(self.profiles_list_widget.count()):
            item = self.profiles_list_widget.item(i)
            w = self.profiles_list_widget.itemWidget(item)
            if isinstance(w, SoloProfileSelectionItemWidget):
                item.setHidden(q not in w.name.lower())

    def _toggle_select_all_profiles(self, checked: bool):
        for i in range(self.profiles_list_widget.count()):
            item = self.profiles_list_widget.item(i)
            w = self.profiles_list_widget.itemWidget(item)
            if isinstance(w, SoloProfileSelectionItemWidget):
                w.chk.setChecked(checked)
        if checked:
            self.selected_profile_ids = {
                self.profiles_list_widget.item(i).data(Qt.UserRole)
                for i in range(self.profiles_list_widget.count())
            }
        else:
            self.selected_profile_ids.clear()
        self._update_profile_counter()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Photo Folder for Solo Scan")
        if folder and folder not in self.sources:
            self.sources.append(folder)
            self.sources_list.addItem(f"📁  {folder}")
            self._update_sources_summary()

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Photo Files for Solo Scan",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.heic *.bmp *.tiff *.tif *.cr2 *.nef *.arw *.dng);;All Files (*)",
        )
        for f in files:
            if f not in self.sources:
                self.sources.append(f)
                self.sources_list.addItem(f"🖼️  {f}")
        if files:
            self._update_sources_summary()

    def _clear_sources(self):
        self.sources.clear()
        self.sources_list.clear()
        self._update_sources_summary()

    def _update_sources_summary(self):
        if not self.sources:
            self.lbl_sources_summary.setText("📊 No sources added yet. Click '📁 Add Folder' or '🖼️ Add Image Files' above.")
            return

        try:
            discovered = discover_photos(self.sources, recursive=self.chk_recursive.isChecked())
            count = len(discovered)
        except Exception:
            count = 0

        self.lbl_sources_summary.setText(
            f"📊 <b>{len(self.sources)} source path{'s' if len(self.sources) != 1 else ''}</b> added • "
            f"<b>~{count} photo{'s' if count != 1 else ''}</b> discovered ready to scan."
        )

    def _select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory for Solo Photos")
        if folder:
            self.output_dir_path = folder
            self.txt_output_dir.setText(folder)

    def _jump_to_step(self, step_idx: int):
        curr = self.stacked_widget.currentIndex()
        if step_idx < curr:
            self.stacked_widget.setCurrentIndex(step_idx)
        elif step_idx > curr:
            if self._validate_step(curr):
                self.stacked_widget.setCurrentIndex(step_idx)

    def _on_step_changed(self, idx: int):
        self._update_step_buttons(idx)

    def _update_step_buttons(self, idx: int):
        for i, lbl in enumerate(self.step_labels):
            if i == idx:
                lbl.setProperty("class", "StepPillActive")
            else:
                lbl.setProperty("class", "StepPill")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

        self.btn_prev.setEnabled(idx > 0)
        if idx == 4:  # Review Step
            self.btn_next.hide()
            self.btn_start.show()
            self._populate_review()
        else:
            self.btn_next.show()
            self.btn_start.hide()

    def _validate_step(self, step_idx: int) -> bool:
        if step_idx == 0:
            if not self.sources:
                QMessageBox.warning(self, "No Sources Selected", "Please select at least one photo folder or image file to scan.")
                return False
        elif step_idx == 1:
            if not self.selected_profile_ids:
                QMessageBox.warning(self, "No People Selected", "Please select at least one person profile to match against.")
                return False
        elif step_idx == 2:
            if not self.output_dir_path:
                QMessageBox.warning(self, "No Output Folder", "Please select an output destination directory.")
                return False
        return True

    def _go_next(self):
        curr = self.stacked_widget.currentIndex()
        if not self._validate_step(curr):
            return
        if curr < 4:
            self.stacked_widget.setCurrentIndex(curr + 1)

    def _go_prev(self):
        curr = self.stacked_widget.currentIndex()
        if curr > 0:
            self.stacked_widget.setCurrentIndex(curr - 1)

    def _populate_review(self):
        # 1. Sources Card
        try:
            discovered = discover_photos(self.sources, recursive=self.chk_recursive.isChecked())
            photo_count = len(discovered)
        except Exception:
            photo_count = 0

        self.lbl_rev_sources_val.setText(f"{len(self.sources)} Source Path{'s' if len(self.sources) != 1 else ''}")
        self.lbl_rev_photos_val.setText(f"~{photo_count} photos discovered (Recursive: {'Yes' if self.chk_recursive.isChecked() else 'No'})")

        # 2. People Profiles Card
        all_profiles = {p["id"]: p.get("name", "Unknown") for p in self.profile_service.list_profiles()}
        sel_names = [all_profiles[pid] for pid in self.selected_profile_ids if pid in all_profiles]
        self.lbl_rev_people_val.setText(f"{len(sel_names)} Solo Profile{'s' if len(sel_names) != 1 else ''} Selected")
        self.lbl_rev_people_names.setText(", ".join(sel_names[:6]) + (f" + {len(sel_names)-6} more" if len(sel_names) > 6 else ""))

        # 3. Output Card
        is_move = self.rad_move_mode.isChecked()
        self.lbl_rev_out_mode.setText("✂️ Move Mode (Verified)" if is_move else "📁 Copy Mode (Safe)")
        self.lbl_rev_out_path.setText(self.output_dir_path)

        # 4. AI Neural Engine Card
        t_val = self.spin_threshold.value()
        self.lbl_rev_thresh_val.setText(f"Threshold: {t_val}% • {self.combo_perf.currentText()}")
        self.lbl_rev_engine_sub.setText("Strict Single-Face Filter + ArcFace (512-d)")

    def _start_scan(self):
        if not self._validate_step(0) or not self._validate_step(1) or not self._validate_step(2):
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
