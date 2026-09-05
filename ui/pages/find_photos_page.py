"""
Find Photos by Person Page Module.

A 4-Step wizard and real-time photo discovery gallery:
1. Select Person (Rich profile grid with search filter)
2. Select Folders (Multi-folder selection with recursive toggle)
3. Choose Photo Type (Interactive 'Solo Photos' vs 'All Photos' cards)
4. Find Photos (Live streaming photo gallery with real-time match rendering, Lightbox inspection, and batch saving)
"""

import datetime
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
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
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config import Config
from domain.face_engine import FaceEngine
from domain.scanner import discover_photos
from services.face_cache_service import FaceCacheService
from services.find_photos_service import FindPhotosService, FindPhotosWorker
from services.profile_service import ProfileService
from services.settings_service import SettingsService
from ui.components.flow_layout import FlowLayout
from ui.components.photo_viewer_dialog import PhotoViewerDialog


def _render_avatar(
    pixmap_path: str | None,
    name: str,
    size: int = 68,
    radius: int | None = None,
    bg_color: str = "#2563eb",
) -> QPixmap:
    """Render a crisp circular or rounded profile avatar with smooth anti-aliasing."""
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
            if radius is not None:
                path.addRoundedRect(0, 0, size, size, radius, radius)
            else:
                path.addEllipse(0, 0, size, size)
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
    if radius is not None:
        painter.drawRoundedRect(0, 0, size, size, radius, radius)
    else:
        painter.drawEllipse(0, 0, size, size)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setPointSize(max(13, size // 3))
    font.setBold(True)
    painter.setFont(font)
    initials = "".join([part[0].upper() for part in name.strip().split()[:2]]) or "P"
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, initials)
    painter.end()
    return target


class PersonCardWidget(QFrame):
    """Modern vertical profile card widget for Step 1."""

    def __init__(self, profile_data: dict[str, Any], is_selected: bool, on_click: Callable[[str], None]):
        super().__init__()
        self.profile_data = profile_data
        self.profile_id = profile_data.get("id", "")
        self.name = profile_data.get("name", "Unknown")
        self.ref_count = profile_data.get("ref_count", 0)
        self.is_selected = is_selected
        self.on_click = on_click

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(185, 205)

        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        # 1. Top status header (badge on top-right)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addStretch()

        self.lbl_selected_badge = QLabel("✓ Selected")
        self.lbl_selected_badge.setStyleSheet(
            "background-color: #10b981; color: #ffffff; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 6px;"
        )
        self.lbl_selected_badge.setVisible(self.is_selected)
        top_row.addWidget(self.lbl_selected_badge)
        layout.addLayout(top_row)

        # 2. Centered Circular Avatar
        first_ref = self.profile_data.get("first_ref_path")
        pix = _render_avatar(first_ref, self.name, size=68)
        self.lbl_avatar = QLabel()
        self.lbl_avatar.setPixmap(pix)
        self.lbl_avatar.setFixedSize(68, 68)
        self.lbl_avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_avatar, 0, Qt.AlignCenter)

        # 3. Person Name
        self.lbl_name = QLabel(self.name)
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff;")
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name, 0, Qt.AlignCenter)

        # 4. Photo Count Pill Badge
        count_text = f"📸 {self.ref_count} photo{'s' if self.ref_count != 1 else ''}"
        self.lbl_refs = QLabel(count_text)
        self.lbl_refs.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 10px; border: 1px solid #334155;"
        )
        self.lbl_refs.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_refs, 0, Qt.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click(self.profile_id)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.lbl_selected_badge.setVisible(selected)
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet(
                "QFrame { background-color: #064e3b; border: 2px solid #10b981; border-radius: 14px; }"
                "QFrame:hover { background-color: #065f46; border: 2px solid #34d399; }"
            )
            self.lbl_refs.setStyleSheet(
                "background-color: #042f24; color: #34d399; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 10px; border: 1px solid #10b981;"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 14px; }"
                "QFrame:hover { background-color: #162238; border: 2px solid #38bdf8; }"
            )
            self.lbl_refs.setStyleSheet(
                "background-color: #1e293b; color: #38bdf8; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 10px; border: 1px solid #334155;"
            )


class MatchModeCard(QFrame):
    """Interactive card for Step 3: choosing Solo Photos vs All Photos."""

    def __init__(self, mode_id: str, title: str, subtitle: str, badge_text: str, icon_emoji: str, is_selected: bool, on_click: Callable[[str], None]):
        super().__init__()
        self.mode_id = mode_id
        self.is_selected = is_selected
        self.on_click = on_click
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(140)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(18)

        # Icon Emoji box
        icon_lbl = QLabel(icon_emoji)
        icon_lbl.setStyleSheet("font-size: 38px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        # Text Info
        info_col = QVBoxLayout()
        info_col.setSpacing(6)
        info_col.setAlignment(Qt.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        title_row.addWidget(self.lbl_title)

        badge_lbl = QLabel(badge_text)
        badge_lbl.setStyleSheet("background-color: #0284c7; color: #ffffff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px;")
        title_row.addWidget(badge_lbl)
        title_row.addStretch()
        info_col.addLayout(title_row)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        info_col.addWidget(lbl_sub)

        layout.addLayout(info_col, 1)

        # Radio indicator
        self.rad = QRadioButton()
        self.rad.setChecked(is_selected)
        self.rad.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.rad.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.rad)

        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click(self.mode_id)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.rad.setChecked(selected)
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet(
                "QFrame { background-color: #0c2033; border: 2px solid #38bdf8; border-radius: 12px; }"
                "QFrame:hover { background-color: #0f2742; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }"
                "QFrame:hover { background-color: #162238; border: 1px solid #38bdf8; }"
            )


class PhotoResultCard(QFrame):
    """Visual gallery card for an individual matched photo with selection checkbox and actions."""

    def __init__(
        self,
        match_info: dict[str, Any],
        on_toggle_select: Callable[[dict[str, Any], bool], None],
        on_view_photo: Callable[[dict[str, Any]], None],
        on_save_photo: Callable[[dict[str, Any]], None],
    ):
        super().__init__()
        self.match_info = match_info
        self.on_toggle_select = on_toggle_select
        self.on_view_photo = on_view_photo
        self.on_save_photo = on_save_photo

        self.is_selected = match_info.get("is_selected", False)
        self.setFixedSize(185, 230)
        self.setCursor(Qt.PointingHandCursor)

        self._setup_ui()
        self._update_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Top Thumbnail Box (with Checkbox & Score Badge overlay)
        thumb_container = QWidget()
        thumb_container.setFixedHeight(140)
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(169, 140)
        self.lbl_thumb.setStyleSheet("background-color: #080c14; border-radius: 8px;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)

        path_str = self.match_info.get("path", "")
        if path_str and Path(path_str).exists():
            pix = QPixmap(path_str)
            if not pix.isNull():
                scaled = pix.scaled(169, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                cropped = QPixmap(169, 140)
                cropped.fill(Qt.transparent)
                painter = QPainter(cropped)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                path = QPainterPath()
                path.addRoundedRect(0, 0, 169, 140, 8, 8)
                painter.setClipPath(path)
                x_off = max(0, (scaled.width() - 169) // 2)
                y_off = max(0, (scaled.height() - 140) // 2)
                painter.drawPixmap(-x_off, -y_off, scaled)
                painter.end()
                self.lbl_thumb.setPixmap(cropped)
            else:
                self.lbl_thumb.setText("📷 Photo")
        else:
            self.lbl_thumb.setText("📷 Photo")

        thumb_layout.addWidget(self.lbl_thumb)
        layout.addWidget(thumb_container)

        # 2. Metadata Info Row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(4)

        score = self.match_info.get("match_score", 0.0)
        badge_score = QLabel(f"🎯 {score}%")
        badge_score.setStyleSheet(
            "background-color: #064e3b; color: #34d399; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px;"
        )
        meta_row.addWidget(badge_score)

        meta_row.addStretch()

        self.chk_select = QCheckBox()
        self.chk_select.setChecked(self.is_selected)
        self.chk_select.setCursor(Qt.PointingHandCursor)
        self.chk_select.toggled.connect(self._on_check_toggled)
        meta_row.addWidget(self.chk_select)

        layout.addLayout(meta_row)

        # 3. Filename
        fname = self.match_info.get("filename", "")
        self.lbl_filename = QLabel(fname)
        self.lbl_filename.setStyleSheet("font-size: 11px; font-weight: 700; color: #ffffff;")
        self.lbl_filename.setToolTip(f"{path_str}\nMatch: {score}%\nModified: {self.match_info.get('formatted_mtime', 'N/A')}")
        layout.addWidget(self.lbl_filename)

        # 4. Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        btn_view = QPushButton("🔍 View")
        btn_view.setCursor(Qt.PointingHandCursor)
        btn_view.setFixedHeight(24)
        btn_view.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; border: 1px solid #3b82f6; border-radius: 4px; font-size: 10px; font-weight: 600; padding: 0 4px; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_view.clicked.connect(lambda: self.on_view_photo(self.match_info))
        btn_row.addWidget(btn_view)

        btn_save = QPushButton("💾 Save")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(24)
        btn_save.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; border: none; border-radius: 4px; font-size: 10px; font-weight: 700; padding: 0 4px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_save.clicked.connect(lambda: self.on_save_photo(self.match_info))
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Toggle checkbox
            self.chk_select.toggle()

    def _on_check_toggled(self, checked: bool):
        self.is_selected = checked
        self.match_info["is_selected"] = checked
        self._update_style()
        self.on_toggle_select(self.match_info, checked)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.match_info["is_selected"] = selected
        self.chk_select.blockSignals(True)
        self.chk_select.setChecked(selected)
        self.chk_select.blockSignals(False)
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet("QFrame { background-color: #064e3b; border: 2px solid #10b981; border-radius: 10px; }")
        else:
            self.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; }"
                "QFrame:hover { border: 1px solid #38bdf8; background-color: #131d33; }"
            )


class FindPhotosPage(QWidget):
    """Modern 4-Step Wizard & Real-Time Photo Discovery Gallery."""

    def __init__(
        self,
        profile_service: ProfileService,
        face_engine: FaceEngine,
        settings_service: SettingsService,
        face_cache_service: FaceCacheService | None = None,
        navigate_cb: Callable[[str], None] | None = None,
    ):
        super().__init__()
        self.profile_service = profile_service
        self.face_engine = face_engine
        self.settings_service = settings_service
        self.face_cache_service = face_cache_service
        self.navigate_cb = navigate_cb
        self.find_service = FindPhotosService()

        # State
        self.selected_profile_id: str | None = None
        self.selected_profile_data: dict[str, Any] | None = None
        self.selected_folders: list[str] = []
        self.match_mode: str = "all"  # "all" or "solo"
        self.matched_photos: list[dict[str, Any]] = []
        self.worker: FindPhotosWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. Page Header Title & Subtitle
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("🔍 Find Photos by Person")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Instantly discover all photos of any person across your folders with real-time match streaming.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_title)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self.btn_header_new_search = QPushButton("🔄 New Search")
        self.btn_header_new_search.setProperty("class", "SecondaryButton")
        self.btn_header_new_search.setCursor(Qt.PointingHandCursor)
        self.btn_header_new_search.setFixedHeight(36)
        self.btn_header_new_search.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_header_new_search.clicked.connect(self._reset_to_step1)
        header_row.addWidget(self.btn_header_new_search)

        main_layout.addLayout(header_row)

        # 2. Step Indicator Progress Bar
        self.step_indicator_card = QFrame()
        self.step_indicator_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 8px 16px;")
        step_ind_l = QHBoxLayout(self.step_indicator_card)
        step_ind_l.setContentsMargins(8, 4, 8, 4)
        step_ind_l.setSpacing(14)

        self.lbl_step1_ind = QLabel("<b>1. Select Person</b>")
        self.lbl_step2_ind = QLabel("2. Select Folders")
        self.lbl_step3_ind = QLabel("3. Choose Photo Type")
        self.lbl_step4_ind = QLabel("4. Live Results Gallery")

        self.step_labels = [self.lbl_step1_ind, self.lbl_step2_ind, self.lbl_step3_ind, self.lbl_step4_ind]
        for idx, lbl in enumerate(self.step_labels):
            step_ind_l.addWidget(lbl)
            if idx < len(self.step_labels) - 1:
                arrow = QLabel("➔")
                arrow.setStyleSheet("color: #475569; font-weight: bold;")
                step_ind_l.addWidget(arrow)

        step_ind_l.addStretch()
        main_layout.addWidget(self.step_indicator_card)

        # 3. Stacked Wizard Pages
        self.wizard_stack = QStackedWidget()

        # Step 1 Widget
        self.step1_widget = self._create_step1_widget()
        self.wizard_stack.addWidget(self.step1_widget)

        # Step 2 Widget
        self.step2_widget = self._create_step2_widget()
        self.wizard_stack.addWidget(self.step2_widget)

        # Step 3 Widget
        self.step3_widget = self._create_step3_widget()
        self.wizard_stack.addWidget(self.step3_widget)

        # Step 4 Widget (Live Gallery & Scanner)
        self.step4_widget = self._create_step4_widget()
        self.wizard_stack.addWidget(self.step4_widget)

        main_layout.addWidget(self.wizard_stack, 1)

        self._update_step_indicator(0)

    # -------------------------------------------------------------------------
    # Step 1: Select Person
    # -------------------------------------------------------------------------
    def _create_step1_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "Card")
        ctrl_l = QHBoxLayout(ctrl_card)
        ctrl_l.setContentsMargins(16, 14, 16, 14)
        ctrl_l.setSpacing(14)

        instruct_col = QVBoxLayout()
        instruct_col.setSpacing(2)
        lbl_instruct = QLabel("<b>Select a Person to Find</b>")
        lbl_instruct.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff;")
        self.lbl_step1_subtitle = QLabel("Choose a person profile to search photos for. Click a profile card below to proceed.")
        self.lbl_step1_subtitle.setStyleSheet("font-size: 12px; color: #94a3b8;")
        instruct_col.addWidget(lbl_instruct)
        instruct_col.addWidget(self.lbl_step1_subtitle)
        ctrl_l.addLayout(instruct_col)

        ctrl_l.addStretch()

        self.txt_search_person = QLineEdit()
        self.txt_search_person.setPlaceholderText("🔍 Search people by name...")
        self.txt_search_person.setFixedWidth(260)
        self.txt_search_person.setStyleSheet(
            "QLineEdit { background-color: #0f172a; border: 1px solid #3b82f6; border-radius: 8px; padding: 8px 14px; font-size: 12px; color: #ffffff; }"
            "QLineEdit:focus { border: 2px solid #38bdf8; background-color: #131d33; }"
        )
        self.txt_search_person.textChanged.connect(self._filter_people_grid)
        ctrl_l.addWidget(self.txt_search_person)

        layout.addWidget(ctrl_card)

        # Profiles Scroll Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.people_grid_content = QWidget()
        self.people_flow_layout = FlowLayout(h_spacing=18, v_spacing=18)
        self.people_grid_content.setLayout(self.people_flow_layout)

        scroll.setWidget(self.people_grid_content)
        layout.addWidget(scroll, 1)

        # Bottom Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()

        self.btn_step1_next = QPushButton("Next: Select Folders ➔")
        self.btn_step1_next.setProperty("class", "PrimaryButton")
        self.btn_step1_next.setCursor(Qt.PointingHandCursor)
        self.btn_step1_next.setEnabled(False)
        self.btn_step1_next.setFixedHeight(42)
        self.btn_step1_next.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 26px; font-size: 14px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
            "QPushButton:disabled { background-color: #1e293b; color: #64748b; border: 1px solid #334155; }"
        )
        self.btn_step1_next.clicked.connect(self._goto_step2)
        bottom_bar.addWidget(self.btn_step1_next)

        layout.addLayout(bottom_bar)
        return w

    # -------------------------------------------------------------------------
    # Step 2: Select Folders
    # -------------------------------------------------------------------------
    def _create_step2_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Selected Person Banner
        self.banner_step2 = QFrame()
        self.banner_step2.setStyleSheet("background-color: #0c1a2e; border: 1px solid #0284c7; border-radius: 10px; padding: 12px 16px;")
        banner_l = QHBoxLayout(self.banner_step2)
        banner_l.setSpacing(14)

        self.lbl_step2_person_avatar = QLabel()
        self.lbl_step2_person_avatar.setFixedSize(40, 40)
        banner_l.addWidget(self.lbl_step2_person_avatar)

        self.lbl_step2_person_name = QLabel("Finding photos for:")
        self.lbl_step2_person_name.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        banner_l.addWidget(self.lbl_step2_person_name, 1)

        btn_change_person = QPushButton("✏️ Change Person")
        btn_change_person.setProperty("class", "SecondaryButton")
        btn_change_person.setCursor(Qt.PointingHandCursor)
        btn_change_person.setStyleSheet("background-color: #1e293b; color: #38bdf8; border-radius: 6px; padding: 4px 12px; font-size: 12px; font-weight: 600;")
        btn_change_person.clicked.connect(self._goto_step1)
        banner_l.addWidget(btn_change_person)

        layout.addWidget(self.banner_step2)

        # Folder Selection Card
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "Card")
        ctrl_l = QVBoxLayout(ctrl_card)
        ctrl_l.setContentsMargins(16, 14, 16, 14)
        ctrl_l.setSpacing(12)

        top_btns = QHBoxLayout()
        top_btns.setSpacing(12)

        btn_choose = QPushButton("📁 Choose Folder")
        btn_choose.setProperty("class", "SecondaryButton")
        btn_choose.setCursor(Qt.PointingHandCursor)
        btn_choose.setFixedHeight(36)
        btn_choose.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_choose.clicked.connect(self._choose_folder)

        btn_add = QPushButton("➕ Add Another Folder")
        btn_add.setProperty("class", "SecondaryButton")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_add.clicked.connect(self._add_folder)

        btn_clear = QPushButton("🗑️ Clear All")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setFixedHeight(36)
        btn_clear.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        btn_clear.clicked.connect(self._clear_folders)

        self.chk_recursive = QCheckBox("🗂️ Include subdirectories (Recursive)")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setCursor(Qt.PointingHandCursor)
        self.chk_recursive.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 13px;")

        top_btns.addWidget(btn_choose)
        top_btns.addWidget(btn_add)
        top_btns.addWidget(btn_clear)
        top_btns.addWidget(self.chk_recursive)
        top_btns.addStretch()
        ctrl_l.addLayout(top_btns)

        # Selected Folders List Widget
        self.list_folders = QListWidget()
        self.list_folders.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 4px; outline: 0px; font-size: 12px; color: #ffffff; }"
            "QListWidget::item { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 8px 12px; margin-bottom: 4px; }"
            "QListWidget::item:hover { background-color: #162238; border: 1px solid #38bdf8; }"
        )
        ctrl_l.addWidget(self.list_folders, 1)

        self.lbl_folder_summary = QLabel("No folder selected.")
        self.lbl_folder_summary.setStyleSheet("color: #38bdf8; font-size: 12px;")
        ctrl_l.addWidget(self.lbl_folder_summary)

        layout.addWidget(ctrl_card, 1)

        # Bottom Bar
        bottom_bar = QHBoxLayout()
        btn_back = QPushButton("← Back to Person")
        btn_back.setProperty("class", "SecondaryButton")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("background-color: #1e293b; color: #ffffff; border-radius: 8px; padding: 0 20px; font-weight: 600; font-size: 13px;")
        btn_back.clicked.connect(self._goto_step1)
        bottom_bar.addWidget(btn_back)

        bottom_bar.addStretch()

        self.btn_step2_next = QPushButton("Next: Choose Photo Type ➔")
        self.btn_step2_next.setProperty("class", "PrimaryButton")
        self.btn_step2_next.setCursor(Qt.PointingHandCursor)
        self.btn_step2_next.setEnabled(False)
        self.btn_step2_next.setFixedHeight(40)
        self.btn_step2_next.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 24px; font-size: 14px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
            "QPushButton:disabled { background-color: #1e293b; color: #64748b; border: 1px solid #334155; }"
        )
        self.btn_step2_next.clicked.connect(self._goto_step3)
        bottom_bar.addWidget(self.btn_step2_next)

        layout.addLayout(bottom_bar)
        return w

    # -------------------------------------------------------------------------
    # Step 3: Choose Photo Type (Solo vs All)
    # -------------------------------------------------------------------------
    def _create_step3_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Header
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "Card")
        ctrl_l = QVBoxLayout(ctrl_card)
        ctrl_l.setContentsMargins(18, 16, 18, 16)
        ctrl_l.setSpacing(12)

        lbl_head = QLabel("<b>Choose Photo Matching Type</b>")
        lbl_head.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        lbl_sub = QLabel("Select whether you want to find only single-person solo photos or all photos containing this person.")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        ctrl_l.addWidget(lbl_head)
        ctrl_l.addWidget(lbl_sub)

        layout.addWidget(ctrl_card)

        # Mode Selection Cards Container
        modes_container = QVBoxLayout()
        modes_container.setSpacing(14)

        self.card_mode_all = MatchModeCard(
            mode_id="all",
            title="All Photos (Solo + Group Photos)",
            subtitle="Find every photo containing the selected person, including solo pictures, family portraits, and group photos with friends.",
            badge_text="✨ Complete Collection",
            icon_emoji="👥",
            is_selected=True,
            on_click=self._select_match_mode,
        )

        self.card_mode_solo = MatchModeCard(
            mode_id="solo",
            title="Solo Photos Only",
            subtitle="Find photos where the selected person is completely ALONE in the photo. Group photos with 2 or more faces are strictly excluded.",
            badge_text="🎯 0% Other Faces",
            icon_emoji="👤",
            is_selected=False,
            on_click=self._select_match_mode,
        )

        modes_container.addWidget(self.card_mode_all)
        modes_container.addWidget(self.card_mode_solo)
        layout.addLayout(modes_container)

        # Search Summary Review Box
        self.summary_review_card = QFrame()
        self.summary_review_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 14px 18px;")
        sum_l = QVBoxLayout(self.summary_review_card)
        sum_l.setSpacing(6)

        lbl_sum_title = QLabel("<b>📋 Search Configuration Summary:</b>")
        lbl_sum_title.setStyleSheet("color: #ffffff; font-size: 13px;")
        self.lbl_sum_person = QLabel("• Person: -")
        self.lbl_sum_person.setStyleSheet("color: #38bdf8; font-size: 12px;")
        self.lbl_sum_folders = QLabel("• Folders: -")
        self.lbl_sum_folders.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        self.lbl_sum_mode = QLabel("• Mode: All Photos")
        self.lbl_sum_mode.setStyleSheet("color: #34d399; font-size: 12px; font-weight: 600;")

        sum_l.addWidget(lbl_sum_title)
        sum_l.addWidget(self.lbl_sum_person)
        sum_l.addWidget(self.lbl_sum_folders)
        sum_l.addWidget(self.lbl_sum_mode)
        layout.addWidget(self.summary_review_card)

        layout.addStretch()

        # Bottom Bar
        bottom_bar = QHBoxLayout()
        btn_back = QPushButton("← Back to Folders")
        btn_back.setProperty("class", "SecondaryButton")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setFixedHeight(40)
        btn_back.setStyleSheet("background-color: #1e293b; color: #ffffff; border-radius: 8px; padding: 0 20px; font-weight: 600; font-size: 13px;")
        btn_back.clicked.connect(self._goto_step2)
        bottom_bar.addWidget(btn_back)

        bottom_bar.addStretch()

        self.btn_start_scan = QPushButton("🚀 Start Finding Photos ➔")
        self.btn_start_scan.setProperty("class", "PrimaryButton")
        self.btn_start_scan.setCursor(Qt.PointingHandCursor)
        self.btn_start_scan.setFixedHeight(40)
        self.btn_start_scan.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 800; border-radius: 8px; padding: 0 28px; font-size: 14px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_start_scan.clicked.connect(self._start_scan)
        bottom_bar.addWidget(self.btn_start_scan)

        layout.addLayout(bottom_bar)
        return w

    # -------------------------------------------------------------------------
    # Step 4: Live Results Gallery & Real-Time Scanner
    # -------------------------------------------------------------------------
    def _create_step4_widget(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 1. Live Scanning Dashboard Hero Bar
        self.scan_dashboard_card = QFrame()
        self.scan_dashboard_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 12px; padding: 14px 18px;")
        dash_l = QVBoxLayout(self.scan_dashboard_card)
        dash_l.setSpacing(10)

        top_status_row = QHBoxLayout()
        top_status_row.setSpacing(12)

        self.lbl_scan_status_title = QLabel("⏳ Finding Photos in Progress...")
        self.lbl_scan_status_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff;")
        top_status_row.addWidget(self.lbl_scan_status_title)

        top_status_row.addStretch()

        self.btn_pause = QPushButton("⏸️ Pause")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setFixedHeight(30)
        self.btn_pause.setStyleSheet("background-color: #1e293b; color: #fbbf24; border: 1px solid #f59e0b; border-radius: 6px; padding: 0 12px; font-weight: 600; font-size: 12px;")
        self.btn_pause.clicked.connect(self._toggle_pause)
        top_status_row.addWidget(self.btn_pause)

        self.btn_cancel_scan = QPushButton("🛑 Stop Search")
        self.btn_cancel_scan.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_scan.setFixedHeight(30)
        self.btn_cancel_scan.setStyleSheet("background-color: #dc2626; color: #ffffff; border: none; border-radius: 6px; padding: 0 12px; font-weight: 700; font-size: 12px;")
        self.btn_cancel_scan.clicked.connect(self._cancel_scan)
        top_status_row.addWidget(self.btn_cancel_scan)

        dash_l.addLayout(top_status_row)

        # Progress bar
        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setFixedHeight(12)
        self.scan_progress_bar.setRange(0, 100)
        self.scan_progress_bar.setValue(0)
        self.scan_progress_bar.setTextVisible(False)
        self.scan_progress_bar.setStyleSheet(
            "QProgressBar { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 6px; }"
            "QProgressBar::chunk { background-color: #10b981; border-radius: 5px; }"
        )
        dash_l.addWidget(self.scan_progress_bar)

        # Metrics stats badges
        stats_row = QHBoxLayout()
        stats_row.setSpacing(18)

        self.lbl_stat_scanned = QLabel("📂 Scanned: 0 / 0")
        self.lbl_stat_scanned.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 600;")

        self.lbl_stat_matches = QLabel("✨ Matches Found: 0")
        self.lbl_stat_matches.setStyleSheet("color: #34d399; font-size: 13px; font-weight: 700;")

        self.lbl_stat_time = QLabel("⏱️ Elapsed: 0.0s")
        self.lbl_stat_time.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 600;")

        self.lbl_current_file = QLabel("")
        self.lbl_current_file.setStyleSheet("color: #64748b; font-size: 11px;")

        stats_row.addWidget(self.lbl_stat_scanned)
        stats_row.addWidget(self.lbl_stat_matches)
        stats_row.addWidget(self.lbl_stat_time)
        stats_row.addWidget(self.lbl_current_file, 1)

        dash_l.addLayout(stats_row)
        layout.addWidget(self.scan_dashboard_card)

        # 2. Results Action Toolbar
        toolbar_card = QFrame()
        toolbar_card.setProperty("class", "Card")
        toolbar_l = QHBoxLayout(toolbar_card)
        toolbar_l.setContentsMargins(14, 10, 14, 10)
        toolbar_l.setSpacing(10)

        btn_select_all = QPushButton("☑️ Select All")
        btn_select_all.setCursor(Qt.PointingHandCursor)
        btn_select_all.setFixedHeight(32)
        btn_select_all.setStyleSheet("background-color: #1e293b; color: #ffffff; border-radius: 6px; padding: 0 12px; font-size: 12px; font-weight: 600;")
        btn_select_all.clicked.connect(self._select_all_photos)
        toolbar_l.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("◻️ Deselect All")
        btn_deselect_all.setCursor(Qt.PointingHandCursor)
        btn_deselect_all.setFixedHeight(32)
        btn_deselect_all.setStyleSheet("background-color: #1e293b; color: #ffffff; border-radius: 6px; padding: 0 12px; font-size: 12px; font-weight: 600;")
        btn_deselect_all.clicked.connect(self._deselect_all_photos)
        toolbar_l.addWidget(btn_deselect_all)

        self.lbl_selected_count = QLabel("0 selected")
        self.lbl_selected_count.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 12px; margin-left: 6px;")
        toolbar_l.addWidget(self.lbl_selected_count)

        toolbar_l.addStretch()

        self.btn_save_selected = QPushButton("💾 Save Selected (0)")
        self.btn_save_selected.setProperty("class", "SecondaryButton")
        self.btn_save_selected.setCursor(Qt.PointingHandCursor)
        self.btn_save_selected.setEnabled(False)
        self.btn_save_selected.setFixedHeight(34)
        self.btn_save_selected.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 6px; padding: 0 16px; font-size: 12px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
            "QPushButton:disabled { background-color: #1e293b; color: #475569; border: 1px solid #334155; }"
        )
        self.btn_save_selected.clicked.connect(self._save_selected_photos)
        toolbar_l.addWidget(self.btn_save_selected)

        self.btn_save_all = QPushButton("📦 Save All Matches (0)")
        self.btn_save_all.setProperty("class", "PrimaryButton")
        self.btn_save_all.setCursor(Qt.PointingHandCursor)
        self.btn_save_all.setEnabled(False)
        self.btn_save_all.setFixedHeight(34)
        self.btn_save_all.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 6px; padding: 0 18px; font-size: 12px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
            "QPushButton:disabled { background-color: #1e293b; color: #475569; border: 1px solid #334155; }"
        )
        self.btn_save_all.clicked.connect(self._save_all_photos)
        toolbar_l.addWidget(self.btn_save_all)

        layout.addWidget(toolbar_card)

        # 3. Real-Time Photos Flow Gallery Scroll Area
        self.gallery_scroll = QScrollArea()
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setStyleSheet("background: transparent; border: none;")

        self.gallery_content = QWidget()
        self.gallery_flow_layout = FlowLayout(h_spacing=12, v_spacing=12)
        self.gallery_content.setLayout(self.gallery_flow_layout)

        self.gallery_scroll.setWidget(self.gallery_content)
        layout.addWidget(self.gallery_scroll, 1)

        return w

    # -------------------------------------------------------------------------
    # Navigation & State Handlers
    # -------------------------------------------------------------------------
    def _update_step_indicator(self, step_idx: int):
        self.wizard_stack.setCurrentIndex(step_idx)
        for idx, lbl in enumerate(self.step_labels):
            if idx == step_idx:
                lbl.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 13px;")
            elif idx < step_idx:
                lbl.setStyleSheet("color: #34d399; font-weight: 700; font-size: 12px;")
            else:
                lbl.setStyleSheet("color: #64748b; font-weight: 500; font-size: 12px;")

    def _goto_step1(self):
        self._update_step_indicator(0)
        self._load_people_grid()

    def _goto_step2(self):
        if not self.selected_profile_id:
            return
        self.selected_profile_data = self.profile_service.get_profile(self.selected_profile_id)
        if not self.selected_profile_data:
            return

        name = self.selected_profile_data.get("name", "Person")
        first_ref = None
        refs = self.selected_profile_data.get("references", [])
        if refs:
            first_ref = refs[0].get("stored_path")
        pix = _render_avatar(first_ref, name, size=40, radius=8)
        self.lbl_step2_person_avatar.setPixmap(pix)
        self.lbl_step2_person_name.setText(f"Finding photos for: <b>{name}</b> ({len(refs)} reference photos)")

        self._update_folders_list_view()
        self._update_step_indicator(1)

    def _goto_step3(self):
        if not self.selected_folders:
            return
        name = self.selected_profile_data.get("name", "Person") if self.selected_profile_data else "Person"
        self.lbl_sum_person.setText(f"• <b>Person:</b> {name}")
        self.lbl_sum_folders.setText(f"• <b>Folders ({len(self.selected_folders)}):</b> {', '.join(self.selected_folders)}")
        mode_text = "All Photos (Solo + Group)" if self.match_mode == "all" else "Solo Photos Only"
        self.lbl_sum_mode.setText(f"• <b>Mode:</b> {mode_text}")
        self._update_step_indicator(2)

    def _reset_to_step1(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        self._goto_step1()

    # -------------------------------------------------------------------------
    # Step 1 People Grid
    # -------------------------------------------------------------------------
    def _load_people_grid(self):
        # Clear existing items in flow layout
        while self.people_flow_layout.count():
            child = self.people_flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        summaries = self.profile_service.list_profiles_summary()
        # Filter out group profiles
        individual_profiles = [p for p in summaries if not p.get("is_group_profile")]

        if not individual_profiles:
            empty_lbl = QLabel("No people profiles found. Go to '👥 People Profiles' to create a profile first.")
            empty_lbl.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 30px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.people_flow_layout.addWidget(empty_lbl)
            self.btn_step1_next.setEnabled(False)
            return

        for p_info in individual_profiles:
            is_sel = p_info["id"] == self.selected_profile_id
            card = PersonCardWidget(
                profile_data=p_info,
                is_selected=is_sel,
                on_click=self._on_person_card_clicked,
            )
            self.people_flow_layout.addWidget(card)

        self.btn_step1_next.setEnabled(bool(self.selected_profile_id))

    def _on_person_card_clicked(self, profile_id: str):
        self.selected_profile_id = profile_id
        # Update cards selection
        for i in range(self.people_flow_layout.count()):
            item = self.people_flow_layout.itemAt(i)
            if item and isinstance(item.widget(), PersonCardWidget):
                w = item.widget()
                w.set_selected(w.profile_id == profile_id)
        self.btn_step1_next.setEnabled(True)

    def _filter_people_grid(self, text: str):
        q = text.strip().lower()
        for i in range(self.people_flow_layout.count()):
            item = self.people_flow_layout.itemAt(i)
            if item and isinstance(item.widget(), PersonCardWidget):
                w = item.widget()
                w.setHidden(q not in w.name.lower())

    # -------------------------------------------------------------------------
    # Step 2 Folders Management
    # -------------------------------------------------------------------------
    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder to Scan")
        if folder:
            p_str = str(Path(folder).resolve())
            self.selected_folders = [p_str]
            self._update_folders_list_view()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Another Folder to Scan")
        if folder:
            p_str = str(Path(folder).resolve())
            if p_str not in self.selected_folders:
                self.selected_folders.append(p_str)
                self._update_folders_list_view()

    def _clear_folders(self):
        self.selected_folders.clear()
        self._update_folders_list_view()

    def _update_folders_list_view(self):
        self.list_folders.clear()
        for f_path in self.selected_folders:
            item = QListWidgetItem(f"📁 {f_path}")
            self.list_folders.addItem(item)

        count = len(self.selected_folders)
        if count == 0:
            self.lbl_folder_summary.setText("No folders selected. Click '📁 Choose Folder' to pick a directory.")
            self.lbl_folder_summary.setStyleSheet("color: #f59e0b; font-size: 12px;")
            self.btn_step2_next.setEnabled(False)
        else:
            self.lbl_folder_summary.setText(f"Selected {count} folder{'s' if count != 1 else ''} to scan.")
            self.lbl_folder_summary.setStyleSheet("color: #38bdf8; font-size: 12px;")
            self.btn_step2_next.setEnabled(True)

    # -------------------------------------------------------------------------
    # Step 3 Match Mode Selection
    # -------------------------------------------------------------------------
    def _select_match_mode(self, mode: str):
        self.match_mode = mode
        self.card_mode_all.set_selected(mode == "all")
        self.card_mode_solo.set_selected(mode == "solo")
        mode_text = "All Photos (Solo + Group)" if mode == "all" else "Solo Photos Only"
        self.lbl_sum_mode.setText(f"• <b>Mode:</b> {mode_text}")

    # -------------------------------------------------------------------------
    # Step 4 Live Scanning & Streaming Gallery
    # -------------------------------------------------------------------------
    def _start_scan(self):
        if not self.selected_profile_data or not self.selected_folders:
            return

        self._update_step_indicator(3)
        self.matched_photos.clear()

        # Clear gallery layout
        while self.gallery_flow_layout.count():
            child = self.gallery_flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Reset UI stats
        self.lbl_scan_status_title.setText("⏳ Finding Photos in Progress...")
        self.lbl_scan_status_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff;")
        self.btn_pause.setText("⏸️ Pause")
        self.btn_pause.setEnabled(True)
        self.btn_cancel_scan.setEnabled(True)
        self.btn_save_selected.setEnabled(False)
        self.btn_save_all.setEnabled(False)
        self.btn_save_selected.setText("💾 Save Selected (0)")
        self.btn_save_all.setText("📦 Save All Matches (0)")
        self.lbl_selected_count.setText("0 selected")
        self.scan_progress_bar.setValue(0)

        threshold = float(self.settings_service.get("matching_threshold", 55.0))

        # Launch Worker
        self.worker = FindPhotosWorker(
            target_profile=self.selected_profile_data,
            folders=self.selected_folders,
            match_type=self.match_mode,
            recursive=self.chk_recursive.isChecked(),
            threshold=threshold,
            face_engine=self.face_engine,
            face_cache_service=self.face_cache_service,
        )

        self.worker.match_found_signal.connect(self._on_realtime_match_found)
        self.worker.progress_signal.connect(self._on_scan_progress)
        self.worker.status_signal.connect(self._on_scan_status)
        self.worker.finished_signal.connect(self._on_scan_finished)
        self.worker.start()

    def _on_realtime_match_found(self, match_info: dict[str, Any]):
        """Real-time slot called immediately when a match is found."""
        self.matched_photos.append(match_info)
        card = PhotoResultCard(
            match_info=match_info,
            on_toggle_select=self._on_photo_selected,
            on_view_photo=self._open_photo_viewer,
            on_save_photo=self._save_single_photo_dialog,
        )
        self.gallery_flow_layout.addWidget(card)

        # Update counter buttons
        m_count = len(self.matched_photos)
        self.lbl_stat_matches.setText(f"✨ Matches Found: {m_count}")
        self.btn_save_all.setText(f"📦 Save All Matches ({m_count})")
        self.btn_save_all.setEnabled(True)

    def _on_scan_progress(self, current: int, total: int, filename: str):
        if total > 0:
            pct = int((current / total) * 100)
            self.scan_progress_bar.setValue(pct)
            self.lbl_stat_scanned.setText(f"📂 Scanned: {current} / {total}")
        self.lbl_current_file.setText(f"Scanning: {filename}")

    def _on_scan_status(self, status: str):
        self.lbl_current_file.setText(status)

    def _on_scan_finished(self, scanned_count: int, matches_count: int, elapsed_sec: float, all_matches: list):
        self.scan_progress_bar.setValue(100)
        self.btn_pause.setEnabled(False)
        self.btn_cancel_scan.setEnabled(False)
        self.lbl_stat_scanned.setText(f"📂 Scanned: {scanned_count} / {scanned_count}")
        self.lbl_stat_matches.setText(f"✨ Matches Found: {matches_count}")
        self.lbl_stat_time.setText(f"⏱️ Total Time: {elapsed_sec:.1f}s")
        self.lbl_current_file.setText("")

        name = self.selected_profile_data.get("name", "Person") if self.selected_profile_data else "Person"

        if matches_count > 0:
            self.lbl_scan_status_title.setText(f"🎉 Search Complete! Found {matches_count} photos of {name} ({elapsed_sec:.1f}s)")
            self.lbl_scan_status_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #34d399;")
            self.btn_save_all.setEnabled(True)
            self.btn_save_all.setText(f"📦 Save All Matches ({matches_count})")
        else:
            self.lbl_scan_status_title.setText(f"Scan finished. No matching photos of {name} found.")
            self.lbl_scan_status_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #fbbf24;")
            # Show empty state in gallery
            empty_frame = QFrame()
            empty_frame.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 12px; padding: 30px;")
            ef_layout = QVBoxLayout(empty_frame)
            ef_layout.setAlignment(Qt.AlignCenter)
            ef_layout.setSpacing(8)

            lbl_icon = QLabel("🔍")
            lbl_icon.setStyleSheet("font-size: 36px; background: transparent;")
            lbl_icon.setAlignment(Qt.AlignCenter)

            lbl_txt = QLabel(f"<b>No photos of {name} found in selected folders.</b>")
            lbl_txt.setStyleSheet("font-size: 15px; color: #ffffff; background: transparent;")
            lbl_txt.setAlignment(Qt.AlignCenter)

            lbl_sub = QLabel("Try scanning additional folders or adding more clear reference photos to their profile.")
            lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent;")
            lbl_sub.setAlignment(Qt.AlignCenter)

            ef_layout.addWidget(lbl_icon)
            ef_layout.addWidget(lbl_txt)
            ef_layout.addWidget(lbl_sub)
            self.gallery_flow_layout.addWidget(empty_frame)

    def _toggle_pause(self):
        if not self.worker:
            return
        if self.worker.is_paused():
            self.worker.resume()
            self.btn_pause.setText("⏸️ Pause")
        else:
            self.worker.pause()
            self.btn_pause.setText("▶️ Resume")

    def _cancel_scan(self):
        if self.worker:
            self.worker.cancel()
            self.lbl_scan_status_title.setText("Search stopped by user.")
            self.btn_pause.setEnabled(False)
            self.btn_cancel_scan.setEnabled(False)

    # -------------------------------------------------------------------------
    # Selection & Save Actions
    # -------------------------------------------------------------------------
    def _on_photo_selected(self, match_info: dict[str, Any], is_checked: bool):
        selected = [p for p in self.matched_photos if p.get("is_selected")]
        cnt = len(selected)
        self.lbl_selected_count.setText(f"{cnt} selected")
        self.btn_save_selected.setText(f"💾 Save Selected ({cnt})")
        self.btn_save_selected.setEnabled(cnt > 0)

    def _select_all_photos(self):
        for i in range(self.gallery_flow_layout.count()):
            item = self.gallery_flow_layout.itemAt(i)
            if item and isinstance(item.widget(), PhotoResultCard):
                item.widget().set_selected(True)
        self._on_photo_selected({}, True)

    def _deselect_all_photos(self):
        for i in range(self.gallery_flow_layout.count()):
            item = self.gallery_flow_layout.itemAt(i)
            if item and isinstance(item.widget(), PhotoResultCard):
                item.widget().set_selected(False)
        self._on_photo_selected({}, False)

    def _open_photo_viewer(self, target_match: dict[str, Any]):
        if not self.matched_photos:
            return
        initial_idx = 0
        for idx, m in enumerate(self.matched_photos):
            if m.get("path") == target_match.get("path"):
                initial_idx = idx
                break

        viewer = PhotoViewerDialog(
            photos_list=self.matched_photos,
            initial_index=initial_idx,
            parent=self,
            save_service=self.find_service,
        )
        viewer.exec()

    def _save_single_photo_dialog(self, match_info: dict[str, Any]):
        src_path = match_info.get("path", "")
        p = Path(src_path)
        if not p.exists():
            QMessageBox.warning(self, "Error", f"Source file does not exist: {p}")
            return

        dest_folder = QFileDialog.getExistingDirectory(self, f"Choose Destination Folder to Save {p.name}")
        if not dest_folder:
            return

        success, target_path, msg = self.find_service.save_single_photo(src_path, dest_folder)
        if success and target_path:
            QMessageBox.information(
                self,
                "Photo Saved",
                f"✨ Successfully saved photo to:\n\n📁 {target_path}",
            )
        else:
            QMessageBox.warning(self, "Save Failed", f"Could not save photo:\n{msg}")

    def _save_selected_photos(self):
        selected_paths = [p["path"] for p in self.matched_photos if p.get("is_selected")]
        if not selected_paths:
            QMessageBox.information(self, "No Selection", "Please select at least one photo to save.")
            return

        dest_folder = QFileDialog.getExistingDirectory(self, f"Choose Destination Folder to Save {len(selected_paths)} Photos")
        if not dest_folder:
            return

        self._execute_batch_save(selected_paths, dest_folder)

    def _save_all_photos(self):
        all_paths = [p["path"] for p in self.matched_photos]
        if not all_paths:
            QMessageBox.information(self, "No Photos", "No matched photos to save.")
            return

        dest_folder = QFileDialog.getExistingDirectory(self, f"Choose Destination Folder to Save All {len(all_paths)} Photos")
        if not dest_folder:
            return

        self._execute_batch_save(all_paths, dest_folder)

    def _execute_batch_save(self, paths: list[str], dest_folder: str):
        total = len(paths)
        prog_dlg = QProgressDialog(f"Saving 1 of {total} photos...", "Cancel", 0, total, self)
        prog_dlg.setWindowTitle("Saving Photos")
        prog_dlg.setWindowModality(Qt.WindowModal)
        prog_dlg.setMinimumDuration(0)
        prog_dlg.setValue(0)
        prog_dlg.setStyleSheet(
            "QProgressDialog { background-color: #0f172a; color: #ffffff; }"
            "QLabel { color: #ffffff; font-size: 12px; }"
            "QPushButton { background-color: #1e293b; color: #f87171; border: 1px solid #dc2626; border-radius: 6px; padding: 4px 12px; }"
            "QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: #ffffff; background: #0b0f19; }"
            "QProgressBar::chunk { background-color: #10b981; border-radius: 5px; }"
        )

        def on_prog(cur: int, tot: int, fname: str):
            prog_dlg.setValue(cur)
            prog_dlg.setLabelText(f"Saving ({cur}/{tot}): {fname}")

        def is_cancelled() -> bool:
            return prog_dlg.wasCanceled()

        success, err, saved_paths = self.find_service.save_multiple_photos(
            paths,
            dest_folder,
            progress_cb=on_prog,
            cancel_check=is_cancelled,
        )

        prog_dlg.close()

        QMessageBox.information(
            self,
            "Save Complete",
            f"✨ Successfully saved {success} photo(s) to:\n\n📁 {dest_folder}"
            + (f"\n\n⚠️ {err} photo(s) could not be saved." if err > 0 else ""),
        )

    def showEvent(self, event):
        super().showEvent(event)
        # If on Step 1, load people grid fresh
        if self.wizard_stack.currentIndex() == 0:
            self._load_people_grid()
