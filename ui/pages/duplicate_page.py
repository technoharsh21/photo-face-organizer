"""
Duplicate Photos Manager Page Module.

Provides an interactive, responsive UI for scanning directories, reviewing duplicate image sets,
comparing side-by-side metadata, applying smart auto-selection rules, providing inline 1-click deletion
per duplicate file, batch cleanup to OS Trash/Quarantine, and instant UI refresh without stale caching.
"""

import datetime
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF, QSize, Qt, QThread, Signal
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
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from services.duplicate_service import DuplicateService, format_bytes
from ui.components.flow_layout import FlowLayout


class DuplicateImageCover(QWidget):
    """Renders a duplicate image thumbnail filled edge-to-edge with rounded corners."""

    def __init__(self, image_path: str | None = None, size: int = 110, radius: int = 8, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.radius = radius
        self.setFixedSize(size, size)
        self.pixmap: QPixmap | None = None

        if image_path and Path(image_path).exists():
            try:
                self.pixmap = QPixmap(str(image_path))
            except Exception:
                self.pixmap = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w = self.width()
        h = self.height()

        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, self.radius, self.radius)
            painter.setClipPath(path)
            x_off = max(0, (scaled.width() - w) // 2)
            y_off = max(0, (scaled.height() - h) // 2)
            painter.drawPixmap(-x_off, -y_off, scaled)
        else:
            painter.setBrush(QColor("#080c14"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, self.radius, self.radius)
            painter.setPen(QColor("#64748b"))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "📷 Photo")
        painter.end()


class DuplicateSetListItemWidget(QWidget):
    """Rich list item card for the duplicate sets navigator sidebar."""

    def __init__(self, sample_name: str, file_count: int, savings_str: str, sample_path: str | None):
        super().__init__()
        self.sample_name = sample_name
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # Thumbnail (44x44)
        thumb = DuplicateImageCover(sample_path, size=44, radius=8)
        thumb.setCursor(Qt.PointingHandCursor)
        layout.addWidget(thumb)

        # Info Box
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        name_lbl = QLabel(sample_name)
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        name_lbl.setCursor(Qt.PointingHandCursor)

        sub_lbl = QLabel(f"📦 {file_count} copies • Reclaim {savings_str}")
        sub_lbl.setStyleSheet("font-size: 11px; color: #38bdf8; background: transparent; border: none; font-weight: 600;")
        sub_lbl.setCursor(Qt.PointingHandCursor)

        info_col.addWidget(name_lbl)
        info_col.addWidget(sub_lbl)
        layout.addLayout(info_col, 1)


class DuplicateFileCard(QFrame):
    """Card representing an individual duplicate copy with metadata, keep toggle, open folder, and inline delete."""

    def __init__(
        self,
        file_info: dict[str, Any],
        on_toggle_keep: Callable[[dict[str, Any], bool], None],
        on_open_location: Callable[[str], None],
        on_delete_file: Callable[[str], None],
    ):
        super().__init__()
        self.file_info = file_info
        self.on_toggle_keep = on_toggle_keep
        self.on_open_location = on_open_location
        self.on_delete_file = on_delete_file

        is_keep = file_info.get("is_recommended_keep", False)
        self.setCursor(Qt.PointingHandCursor)

        row_l = QHBoxLayout(self)
        row_l.setContentsMargins(12, 10, 12, 10)
        row_l.setSpacing(14)

        # 1. Image Thumbnail
        p_str = file_info["path"]
        self.thumb = DuplicateImageCover(p_str, size=110, radius=8)
        self.thumb.setCursor(Qt.PointingHandCursor)
        row_l.addWidget(self.thumb)

        # 2. File Metadata
        info_l = QVBoxLayout()
        info_l.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        name_lbl = QLabel(f"<b>{file_info['filename']}</b>")
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        title_row.addWidget(name_lbl)

        # Status badge
        self.badge_lbl = QLabel("🟢 Recommended Original" if is_keep else "⚠️ Duplicate Copy")
        title_row.addWidget(self.badge_lbl)
        title_row.addStretch()
        info_l.addLayout(title_row)

        path_lbl = QLabel(f"<b>Path:</b> {p_str}")
        path_lbl.setWordWrap(True)
        path_lbl.setToolTip(p_str)
        path_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1;")
        info_l.addWidget(path_lbl)

        meta_lbl = QLabel(f"💾 Size: <b>{file_info['formatted_size']}</b> • 📅 Modified: {file_info['formatted_mtime']}")
        meta_lbl.setStyleSheet("font-size: 12px; color: #38bdf8;")
        info_l.addWidget(meta_lbl)

        row_l.addLayout(info_l, 1)

        # 3. Action Controls Column
        ctrl_l = QVBoxLayout()
        ctrl_l.setSpacing(8)
        ctrl_l.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        # Keep Radio Button
        self.rad_keep = QRadioButton("🟢 Keep This Copy")
        self.rad_keep.setChecked(is_keep)
        self.rad_keep.setCursor(Qt.PointingHandCursor)
        self.rad_keep.setStyleSheet("color: #34d399; font-weight: 700; font-size: 12px;")
        self.rad_keep.toggled.connect(lambda chk: self.on_toggle_keep(self.file_info, chk))
        ctrl_l.addWidget(self.rad_keep)

        # Bottom buttons row (Open Location + Inline Delete Button)
        btn_sub_row = QHBoxLayout()
        btn_sub_row.setSpacing(6)

        btn_open = QPushButton("📂 Open Folder")
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setFixedHeight(28)
        btn_open.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; border: 1px solid #3b82f6; border-radius: 6px; padding: 0 10px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_open.clicked.connect(lambda: self.on_open_location(p_str))
        btn_sub_row.addWidget(btn_open)

        # Inline Individual Delete Button
        self.btn_del_single = QPushButton("🗑️ Delete")
        self.btn_del_single.setProperty("class", "DangerButton")
        self.btn_del_single.setCursor(Qt.PointingHandCursor)
        self.btn_del_single.setFixedHeight(28)
        self.btn_del_single.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 6px; padding: 0 10px; font-size: 11px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
            "QPushButton:disabled { background-color: #78350f; color: #fbbf24; border: 1px solid #f59e0b; }"
        )
        self.btn_del_single.clicked.connect(lambda: self.on_delete_file(p_str, self))
        btn_sub_row.addWidget(self.btn_del_single)

        ctrl_l.addLayout(btn_sub_row)
        row_l.addLayout(ctrl_l)

        self._update_style(is_keep)

    def set_deleting_state(self):
        """Immediately display clear visual loading state on this duplicate card."""
        self.btn_del_single.setEnabled(False)
        self.btn_del_single.setText("⏳ Deleting...")
        self.rad_keep.setEnabled(False)
        self.badge_lbl.setText("⏳ Deleting from disk...")
        self.badge_lbl.setStyleSheet(
            "background-color: #78350f; color: #fbbf24; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px dashed #f59e0b;"
        )
        self.setStyleSheet("QFrame { background-color: #1c1515; border: 2px dashed #f59e0b; border-radius: 10px; }")

    def reset_state(self):
        """Restore card state if deletion was canceled or encountered an error."""
        is_keep = self.file_info.get("is_recommended_keep", False)
        self.btn_del_single.setEnabled(True)
        self.btn_del_single.setText("🗑️ Delete")
        self.rad_keep.setEnabled(True)
        self._update_style(is_keep)

    def _update_style(self, is_keep: bool):
        if is_keep:
            self.setStyleSheet("QFrame { background-color: #064e3b; border: 2px solid #10b981; border-radius: 10px; }")
            self.badge_lbl.setText("🟢 Recommended Original")
            self.badge_lbl.setStyleSheet(
                "background-color: #064e3b; color: #34d399; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid #10b981;"
            )
        else:
            self.setStyleSheet("QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; } QFrame:hover { border: 1px solid #38bdf8; }")
            self.badge_lbl.setText("⚠️ Duplicate Copy")
            self.badge_lbl.setStyleSheet(
                "background-color: #78350f; color: #fbbf24; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; border: 1px solid #f59e0b;"
            )


class DuplicateScanWorker(QThread):
    """Background worker thread for scanning duplicate images without UI freeze."""

    finished_signal = Signal(list)

    def __init__(self, duplicate_service: DuplicateService, sources: list[str], recursive: bool):
        super().__init__()
        self.duplicate_service = duplicate_service
        self.sources = sources
        self.recursive = recursive

    def run(self):
        try:
            sets = self.duplicate_service.scan_directories_for_duplicates(
                sources=self.sources,
                recursive=self.recursive,
            )
            self.finished_signal.emit(sets)
        except Exception:
            self.finished_signal.emit([])


class DuplicateBatchActionWorker(QThread):
    """Background worker thread for deleting or quarantining large volumes of duplicate files safely."""

    progress_signal = Signal(int, int, str)
    finished_signal = Signal(int, int, int)

    def __init__(self, duplicate_service: DuplicateService, file_paths: list[str], mode: str):
        super().__init__()
        self.duplicate_service = duplicate_service
        self.file_paths = file_paths
        self.mode = mode
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        def on_prog(cur: int, tot: int, fname: str):
            self.progress_signal.emit(cur, tot, fname)

        def is_cancelled() -> bool:
            return self._is_cancelled

        success, err, freed = self.duplicate_service.remove_duplicates(
            self.file_paths,
            mode=self.mode,
            progress_cb=on_prog,
            cancel_check=is_cancelled,
        )
        self.finished_signal.emit(success, err, freed)


class DuplicatePage(QWidget):
    """Modern UI Page for inspecting, managing, and cleaning duplicate photo files with inline deletion."""

    def __init__(self, duplicate_service: DuplicateService):
        super().__init__()
        self.duplicate_service = duplicate_service
        self.default_source: str = str(Path.home() / "Pictures" / "Organized_Photos")
        self.sources: list[str] = [self.default_source] if Path(self.default_source).exists() else []
        self.duplicate_sets: list[dict[str, Any]] = []
        self.current_set_id: str | None = None
        self.worker: DuplicateScanWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Header Title & Actions
        header_l = QHBoxLayout()
        header_l.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("🔍 Duplicate Photos Manager")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Identify identical duplicate photos using SHA-256 byte hashing and safely reclaim disk storage.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_title)
        header_l.addLayout(title_box)

        header_l.addStretch()

        self.btn_rescan_hdr = QPushButton("🔄 Rescan Duplicates")
        self.btn_rescan_hdr.setProperty("class", "SecondaryButton")
        self.btn_rescan_hdr.setCursor(Qt.PointingHandCursor)
        self.btn_rescan_hdr.setFixedHeight(36)
        self.btn_rescan_hdr.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_rescan_hdr.clicked.connect(self._run_duplicate_scan)
        header_l.addWidget(self.btn_rescan_hdr)

        layout.addLayout(header_l)

        # 2. Control Bar Card (Target Folder Selection & Scan Action)
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "Card")
        ctrl_l = QVBoxLayout(ctrl_card)
        ctrl_l.setContentsMargins(14, 12, 14, 12)
        ctrl_l.setSpacing(10)

        top_btns = QHBoxLayout()
        top_btns.setSpacing(12)

        btn_add_folder = QPushButton("📁 Add Folder to Scan")
        btn_add_folder.setProperty("class", "SecondaryButton")
        btn_add_folder.setCursor(Qt.PointingHandCursor)
        btn_add_folder.setFixedHeight(36)
        btn_add_folder.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_add_folder.clicked.connect(self._add_folder)

        btn_clear = QPushButton("🗑️ Clear Folders")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setFixedHeight(36)
        btn_clear.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        btn_clear.clicked.connect(self._clear_folders)

        self.chk_recursive = QCheckBox("🗂️ Scan subdirectories recursively")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setCursor(Qt.PointingHandCursor)
        self.chk_recursive.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 13px;")

        self.btn_scan = QPushButton("⚡ Scan for Duplicates")
        self.btn_scan.setProperty("class", "PrimaryButton")
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.setFixedHeight(36)
        self.btn_scan.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_scan.clicked.connect(self._run_duplicate_scan)

        top_btns.addWidget(btn_add_folder)
        top_btns.addWidget(btn_clear)
        top_btns.addWidget(self.chk_recursive)
        top_btns.addStretch()
        top_btns.addWidget(self.btn_scan)
        ctrl_l.addLayout(top_btns)

        self.sources_lbl = QLabel(f"<b>Scan Targets:</b> {', '.join(self.sources) if self.sources else 'Default Output Folder (~/Pictures/Organized_Photos)'}")
        self.sources_lbl.setStyleSheet("color: #38bdf8; font-size: 12px;")
        ctrl_l.addWidget(self.sources_lbl)

        # Loading Status Indicator Banner
        self.lbl_loading_status = QLabel("")
        self.lbl_loading_status.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 13px;")
        self.lbl_loading_status.hide()
        ctrl_l.addWidget(self.lbl_loading_status)

        layout.addWidget(ctrl_card)

        # 3. Summary Stats Hero Bar
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 10px 16px;")
        sum_l = QHBoxLayout(self.summary_card)
        sum_l.setContentsMargins(10, 6, 10, 6)
        sum_l.setSpacing(16)

        self.lbl_sum_sets = QLabel("🔍 Duplicate Groups: 0")
        self.lbl_sum_sets.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.lbl_sum_files = QLabel("📦 Duplicate Copies: 0")
        self.lbl_sum_files.setStyleSheet("color: #f87171; font-weight: bold; font-size: 13px;")
        self.lbl_sum_savings = QLabel("💾 Reclaimable Space: 0 B")
        self.lbl_sum_savings.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")

        sum_l.addWidget(self.lbl_sum_sets)
        sum_l.addWidget(self.lbl_sum_files)
        sum_l.addWidget(self.lbl_sum_savings)
        sum_l.addStretch()
        layout.addWidget(self.summary_card)

        # 4. Main Splitter (Left: Sets List, Right: Comparison Grid & Actions)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Sets List Widget
        left_w = QFrame()
        left_w.setProperty("class", "Card")
        left_w.setMinimumWidth(280)
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(14, 14, 14, 14)
        left_l.setSpacing(10)

        left_hdr_row = QHBoxLayout()
        left_hdr = QLabel("<b>Duplicate Groups</b>")
        left_hdr.setStyleSheet("font-size: 14px; color: #ffffff;")
        self.lbl_group_count = QLabel("0 Groups")
        self.lbl_group_count.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        left_hdr_row.addWidget(left_hdr)
        left_hdr_row.addStretch()
        left_hdr_row.addWidget(self.lbl_group_count)
        left_l.addLayout(left_hdr_row)

        # Search filter
        self.txt_filter_sets = QLineEdit()
        self.txt_filter_sets.setPlaceholderText("🔍 Filter duplicate groups...")
        self.txt_filter_sets.setStyleSheet(
            "QLineEdit { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 6px 12px; font-size: 12px; color: #ffffff; }"
            "QLineEdit:focus { border: 2px solid #67e8f9; background-color: #131d33; }"
        )
        self.txt_filter_sets.textChanged.connect(self._filter_sets_list)
        left_l.addWidget(self.txt_filter_sets)

        self.sets_list_widget = QListWidget()
        self.sets_list_widget.setCursor(Qt.PointingHandCursor)
        self.sets_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sets_list_widget.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; padding: 4px; outline: 0px; }"
            "QListWidget::item { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 4px; padding: 2px; }"
            "QListWidget::item:hover { background-color: #162238; border: 1px solid #38bdf8; }"
            "QListWidget::item:selected { background-color: #1e293b; border: 1px solid #38bdf8; }"
        )
        self.sets_list_widget.itemSelectionChanged.connect(self._on_set_selected)
        left_l.addWidget(self.sets_list_widget, 1)

        splitter.addWidget(left_w)

        # Right: Detail & Action Area
        right_frame = QFrame()
        right_frame.setProperty("class", "Card")
        right_l = QVBoxLayout(right_frame)
        right_l.setContentsMargins(16, 16, 16, 16)
        right_l.setSpacing(12)

        # Actions Toolbar — wraps on narrow windows so button text never clips
        actions_l = FlowLayout(h_spacing=8, v_spacing=8)

        lbl_rule = QLabel("<b>Rule:</b>")
        lbl_rule.setStyleSheet("color: #ffffff; font-size: 12px;")
        actions_l.addWidget(lbl_rule)

        self.combo_rule = QComboBox()
        self.combo_rule.setCursor(Qt.PointingHandCursor)
        self.combo_rule.addItems(["Keep Oldest (Original)", "Keep Newest Copy", "Keep Shortest Path"])
        actions_l.addWidget(self.combo_rule)

        btn_auto_select = QPushButton("⚡ Auto Select")
        btn_auto_select.setProperty("class", "SecondaryButton")
        btn_auto_select.setCursor(Qt.PointingHandCursor)
        btn_auto_select.setFixedHeight(36)
        btn_auto_select.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_auto_select.clicked.connect(self._apply_auto_select_rule)
        actions_l.addWidget(btn_auto_select)

        self.btn_quarantine = QPushButton("📁 Quarantine Selected")
        self.btn_quarantine.setProperty("class", "SecondaryButton")
        self.btn_quarantine.setCursor(Qt.PointingHandCursor)
        self.btn_quarantine.setFixedHeight(36)
        self.btn_quarantine.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_quarantine.setToolTip("Move selected duplicate copies to a safe Quarantine folder.")
        self.btn_quarantine.clicked.connect(self._quarantine_selected)
        actions_l.addWidget(self.btn_quarantine)

        self.btn_delete = QPushButton("🗑️ Delete Selected Copies")
        self.btn_delete.setProperty("class", "DangerButton")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedHeight(36)
        self.btn_delete.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: none; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        self.btn_delete.setToolTip("Safely delete selected duplicate photos to recycle bin.")
        self.btn_delete.clicked.connect(self._delete_selected)
        actions_l.addWidget(self.btn_delete)

        right_l.addLayout(actions_l)

        # Comparison Files Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.files_layout = QVBoxLayout(self.scroll_content)
        self.files_layout.setContentsMargins(4, 4, 4, 4)
        self.files_layout.setSpacing(12)
        self.files_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.scroll_content)
        right_l.addWidget(self.scroll, 1)

        splitter.addWidget(right_frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)
        self.refresh()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Duplicates")
        if folder:
            p_str = str(Path(folder).resolve())
            if p_str not in self.sources:
                self.sources.append(p_str)
                self._update_sources_label()

    def _clear_folders(self):
        self.sources.clear()
        self._update_sources_label()

    def _update_sources_label(self):
        if not self.sources:
            self.sources_lbl.setText("<b>Scan Targets:</b> No folder selected. Click '📁 Add Folder to Scan' to choose a directory.")
            self.sources_lbl.setStyleSheet("color: #f59e0b; font-size: 12px;")
        else:
            targets_str = " | ".join(self.sources)
            self.sources_lbl.setText(f"<b>Target Folders ({len(self.sources)}):</b> {targets_str}")
            self.sources_lbl.setStyleSheet("color: #38bdf8; font-size: 12px;")

    def _run_duplicate_scan(self):
        if not self.sources:
            default_p = str(Path.home() / "Pictures" / "Organized_Photos")
            if Path(default_p).exists():
                self.sources = [default_p]
                self._update_sources_label()
            else:
                folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Duplicates")
                if folder:
                    self.sources.append(str(Path(folder).resolve()))
                    self._update_sources_label()
                else:
                    return

        scan_targets = list(self.sources)

        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("⏳ Scanning... Please wait")
        self.btn_rescan_hdr.setEnabled(False)
        self.lbl_loading_status.setText(f"⏳ Scanning {len(scan_targets)} folder(s) for duplicate photos... Please wait.")
        self.lbl_loading_status.show()

        self.worker = DuplicateScanWorker(
            duplicate_service=self.duplicate_service,
            sources=scan_targets,
            recursive=self.chk_recursive.isChecked(),
        )
        self.worker.finished_signal.connect(self._on_scan_finished)
        self.worker.start()

    def _on_scan_finished(self, duplicate_sets: list[dict[str, Any]]):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("⚡ Scan for Duplicates")
        self.btn_rescan_hdr.setEnabled(True)
        self.lbl_loading_status.hide()
        self.duplicate_sets = duplicate_sets
        self.refresh()

    def refresh(self):
        """Refresh duplicate sets list and summary bar while preserving active selection."""
        target_set_id = self.current_set_id
        self.sets_list_widget.blockSignals(True)
        self.sets_list_widget.clear()

        # Clean out any duplicate sets that have <= 1 file remaining
        self.duplicate_sets = [d for d in self.duplicate_sets if len(d.get("files", [])) >= 2]

        total_files_cnt = 0
        total_savings_bytes = 0
        select_row = -1

        for idx, dset in enumerate(self.duplicate_sets):
            set_id = dset["set_id"]
            name = dset["sample_name"]
            files = dset.get("files", [])
            f_cnt = len(files)
            single_size = dset.get("single_size", 0)
            potential_savings = single_size * (f_cnt - 1)
            savings_str = format_bytes(potential_savings)
            dset["file_count"] = f_cnt
            dset["potential_savings"] = potential_savings
            dset["formatted_savings"] = savings_str

            total_files_cnt += f_cnt
            total_savings_bytes += potential_savings

            first_path = files[0]["path"] if files else None

            item = QListWidgetItem()
            item.setData(Qt.UserRole, set_id)
            item.setSizeHint(QSize(200, 60))
            self.sets_list_widget.addItem(item)

            widget = DuplicateSetListItemWidget(
                sample_name=name,
                file_count=f_cnt,
                savings_str=savings_str,
                sample_path=first_path,
            )
            self.sets_list_widget.setItemWidget(item, widget)

            if target_set_id and set_id == target_set_id:
                select_row = idx

        self.sets_list_widget.blockSignals(False)

        # Update Summary Labels
        self.lbl_sum_sets.setText(f"🔍 Duplicate Groups: {len(self.duplicate_sets)}")
        self.lbl_sum_files.setText(f"📦 Duplicate Copies: {total_files_cnt}")
        self.lbl_sum_savings.setText(f"💾 Reclaimable Space: {format_bytes(total_savings_bytes)}")
        self.lbl_group_count.setText(f"{len(self.duplicate_sets)} Group{'s' if len(self.duplicate_sets) != 1 else ''}")

        if self.sets_list_widget.count() > 0:
            if select_row >= 0:
                self.sets_list_widget.setCurrentRow(select_row)
            else:
                self.sets_list_widget.setCurrentRow(0)
            items = self.sets_list_widget.selectedItems()
            if items:
                active_id = items[0].data(Qt.UserRole)
                dset = next((s for s in self.duplicate_sets if s["set_id"] == active_id), None)
                if dset:
                    self._display_set_files(dset)
        else:
            self.current_set_id = None
            self._clear_files_layout()
            empty_frame = QFrame()
            empty_frame.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 12px; padding: 40px;")
            ef_layout = QVBoxLayout(empty_frame)
            ef_layout.setAlignment(Qt.AlignCenter)
            ef_layout.setSpacing(10)

            icon_lbl = QLabel("🎉")
            icon_lbl.setStyleSheet("font-size: 40px; background: transparent; border: none;")
            icon_lbl.setAlignment(Qt.AlignCenter)

            lbl_empty = QLabel("<b>All Clean! No duplicate image files found.</b>")
            lbl_empty.setStyleSheet("font-size: 16px; color: #34d399; background: transparent; border: none;")
            lbl_empty.setAlignment(Qt.AlignCenter)

            lbl_sub_empty = QLabel("Your scanned photo directories are 100% deduplicated and organized.")
            lbl_sub_empty.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent; border: none;")
            lbl_sub_empty.setAlignment(Qt.AlignCenter)

            ef_layout.addWidget(icon_lbl)
            ef_layout.addWidget(lbl_empty)
            ef_layout.addWidget(lbl_sub_empty)
            self.files_layout.addWidget(empty_frame)

    def _filter_sets_list(self, query: str):
        q = query.strip().lower()
        for i in range(self.sets_list_widget.count()):
            item = self.sets_list_widget.item(i)
            w = self.sets_list_widget.itemWidget(item)
            if isinstance(w, DuplicateSetListItemWidget):
                item.setHidden(q not in w.sample_name.lower())

    def _on_set_selected(self):
        items = self.sets_list_widget.selectedItems()
        if not items:
            self.current_set_id = None
            self._clear_files_layout()
            return

        set_id = items[0].data(Qt.UserRole)
        self.current_set_id = set_id

        dset = next((s for s in self.duplicate_sets if s["set_id"] == set_id), None)
        if dset:
            self._display_set_files(dset)

    def _clear_files_layout(self):
        while self.files_layout.count():
            child = self.files_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _display_set_files(self, dset: dict[str, Any]):
        self._clear_files_layout()
        files = dset.get("files", [])

        # Ensure at least 1 file is marked as keep
        if files and not any(f.get("is_recommended_keep") for f in files):
            files[0]["is_recommended_keep"] = True
            for f in files[1:]:
                f["is_selected_for_removal"] = True

        for f_info in files:
            card = DuplicateFileCard(
                file_info=f_info,
                on_toggle_keep=self._toggle_keep,
                on_open_location=self._open_file_location,
                on_delete_file=lambda path, c, s_id=dset["set_id"]: self._delete_single_file(s_id, path, c),
            )
            self.files_layout.addWidget(card)

    def _toggle_keep(self, target_file_info: dict[str, Any], is_checked: bool):
        if not is_checked or not self.current_set_id:
            return

        dset = next((s for s in self.duplicate_sets if s["set_id"] == self.current_set_id), None)
        if dset:
            for fi in dset.get("files", []):
                if fi["path"] == target_file_info["path"]:
                    fi["is_recommended_keep"] = True
                    fi["is_selected_for_removal"] = False
                else:
                    fi["is_recommended_keep"] = False
                    fi["is_selected_for_removal"] = True

            self._display_set_files(dset)

    def _open_file_location(self, file_path_str: str):
        p = Path(file_path_str)
        if not p.exists():
            return

        folder = str(p.parent)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _delete_single_file(self, set_id: str, file_path_str: str, card: DuplicateFileCard | None = None):
        """Direct inline deletion of an individual duplicate file with instant list removal and loading indicator."""
        p = Path(file_path_str)
        fname = p.name

        confirm = QMessageBox.question(
            self,
            "Confirm Delete Duplicate File",
            f"Are you sure you want to delete this duplicate copy?\n\n📁 {fname}\n\nThis file will be safely sent to Trash.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        if card:
            card.set_deleting_state()

        self.lbl_loading_status.setText(f"⏳ Deleting duplicate file '{fname}' to Trash... Please wait.")
        self.lbl_loading_status.show()

        worker = DuplicateBatchActionWorker(self.duplicate_service, [file_path_str], mode="trash")

        def on_finished(success: int, err: int, freed: int):
            self.lbl_loading_status.hide()
            if success > 0:
                # Find and update the duplicate set in memory immediately
                dset = next((s for s in self.duplicate_sets if s["set_id"] == set_id), None)
                if dset:
                    dset["files"] = [f for f in dset.get("files", []) if f["path"] != file_path_str]
                    if len(dset["files"]) <= 1:
                        # Group is no longer a duplicate set since only 1 copy remains
                        self.duplicate_sets = [s for s in self.duplicate_sets if s["set_id"] != set_id]
                    else:
                        dset["file_count"] = len(dset["files"])
                        if not any(f.get("is_recommended_keep") for f in dset["files"]):
                            dset["files"][0]["is_recommended_keep"] = True
                            for f in dset["files"][1:]:
                                f["is_selected_for_removal"] = True

                self.refresh()
            else:
                if card:
                    card.reset_state()
                QMessageBox.warning(self, "Delete Error", f"Could not delete '{fname}'. Please check file permissions.")

        worker.finished_signal.connect(on_finished)
        worker.start()
        self._single_del_worker = worker

    def _apply_auto_select_rule(self):
        text = self.combo_rule.currentText()
        rule_key = "keep_oldest"
        if "Newest" in text:
            rule_key = "keep_newest"
        elif "Shortest" in text:
            rule_key = "keep_shortest_path"

        self.duplicate_service.apply_auto_select_rule(self.duplicate_sets, rule=rule_key)
        if self.current_set_id:
            dset = next((s for s in self.duplicate_sets if s["set_id"] == self.current_set_id), None)
            if dset:
                self._display_set_files(dset)
        self.refresh()

    def _get_all_files_selected_for_removal(self) -> list[str]:
        to_remove = []
        for dset in self.duplicate_sets:
            for fi in dset.get("files", []):
                if fi.get("is_selected_for_removal") and not fi.get("is_recommended_keep"):
                    to_remove.append(fi["path"])
        return to_remove

    def _quarantine_selected(self):
        to_remove = self._get_all_files_selected_for_removal()
        if not to_remove:
            QMessageBox.information(self, "No Selection", "No duplicate files selected for removal.")
            return

        confirm = QMessageBox.question(
            self,
            "Quarantine Selected Duplicates",
            f"Are you sure you want to move {len(to_remove)} duplicate files to the Quarantine folder?\n\nOriginal files marked 'Keep This Copy' will remain in place.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self._execute_batch_action(to_remove, mode="quarantine", title="Quarantining Duplicate Files")

    def _delete_selected(self):
        to_remove = self._get_all_files_selected_for_removal()
        if not to_remove:
            QMessageBox.information(self, "No Selection", "No duplicate files selected for removal.")
            return

        confirm = QMessageBox.question(
            self,
            "Send Duplicates to Trash",
            f"Are you sure you want to send {len(to_remove)} duplicate files to the Trash / Recycle Bin?\n\nOriginal files marked 'Keep This Copy' will remain untouched.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self._execute_batch_action(to_remove, mode="trash", title="Deleting Duplicate Files")

    def _execute_batch_action(self, to_remove: list[str], mode: str, title: str):
        total = len(to_remove)
        action_name = "quarantined" if mode == "quarantine" else "sent to Trash"

        prog_dlg = QProgressDialog(f"Processing 1 of {total}...", "Cancel", 0, total, self)
        prog_dlg.setWindowTitle(title)
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

        worker = DuplicateBatchActionWorker(self.duplicate_service, to_remove, mode)

        def on_prog(cur: int, tot: int, fname: str):
            prog_dlg.setValue(cur)
            prog_dlg.setLabelText(f"Processing ({cur}/{tot}): {fname}")

        def on_finish(success: int, err: int, freed: int):
            prog_dlg.close()
            rem_set = set(to_remove[:success])
            for dset in self.duplicate_sets:
                dset["files"] = [f for f in dset.get("files", []) if f["path"] not in rem_set]
            self.duplicate_sets = [s for s in self.duplicate_sets if len(s.get("files", [])) >= 2]
            self.refresh()
            QMessageBox.information(
                self,
                "Batch Cleanup Complete",
                f"✨ Successfully {action_name} {success} duplicate file(s).\n\n💾 Reclaimed {format_bytes(freed)} of disk space.",
            )

        prog_dlg.canceled.connect(worker.cancel)
        worker.progress_signal.connect(on_prog)
        worker.finished_signal.connect(on_finish)
        worker.start()
        self.batch_worker = worker
