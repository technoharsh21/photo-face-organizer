"""
Duplicate Photos Manager Page Module.

Provides interactive UI for scanning directories, reviewing duplicate image sets,
comparing side-by-side metadata, applying smart auto-selection rules,
and safely sending duplicate files to OS Trash or Quarantine.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from services.duplicate_service import DuplicateService, format_bytes


class DuplicatePage(QWidget):
    """UI Page for inspecting and cleaning duplicate image files."""

    def __init__(self, duplicate_service: DuplicateService):
        super().__init__()
        self.duplicate_service = duplicate_service
        self.sources: list[str] = []
        self.duplicate_sets: list[dict[str, Any]] = []
        self.current_set_id: str | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title & Subtitle
        header_l = QVBoxLayout()
        header_l.setSpacing(4)
        title_lbl = QLabel("🔍 Duplicate Photos Manager")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        sub_title = QLabel("Scan folders for exact duplicate images, compare side-by-side, and safely reclaim disk space.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        header_l.addWidget(title_lbl)
        header_l.addWidget(sub_title)
        layout.addLayout(header_l)

        # Top Control Bar (Source Folders Selection & Scan Action)
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "Card")
        ctrl_l = QVBoxLayout(ctrl_card)
        ctrl_l.setContentsMargins(12, 12, 12, 12)
        ctrl_l.setSpacing(10)

        top_btns = QHBoxLayout()
        btn_add_folder = QPushButton("📁 Add Folder to Scan")
        btn_add_folder.setProperty("class", "SecondaryButton")
        btn_add_folder.clicked.connect(self._add_folder)

        btn_clear = QPushButton("Clear Folders")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.clicked.connect(self._clear_folders)

        self.chk_recursive = QCheckBox("Scan subdirectories recursively")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setStyleSheet("color: #ffffff;")

        self.btn_scan = QPushButton("⚡ Scan for Duplicates")
        self.btn_scan.setProperty("class", "PrimaryButton")
        self.btn_scan.clicked.connect(self._run_duplicate_scan)

        top_btns.addWidget(btn_add_folder)
        top_btns.addWidget(btn_clear)
        top_btns.addWidget(self.chk_recursive)
        top_btns.addStretch()
        top_btns.addWidget(self.btn_scan)
        ctrl_l.addLayout(top_btns)

        self.sources_lbl = QLabel("<b>Scan Targets:</b> Default Output Folder (~/Pictures/Organized_Photos)")
        self.sources_lbl.setStyleSheet("color: #60a5fa; font-size: 12px;")
        ctrl_l.addWidget(self.sources_lbl)

        layout.addWidget(ctrl_card)

        # Summary Bar Card
        self.summary_card = QFrame()
        self.summary_card.setProperty("class", "Card")
        self.summary_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 8px;")
        sum_l = QHBoxLayout(self.summary_card)
        sum_l.setContentsMargins(12, 6, 12, 6)

        self.lbl_sum_sets = QLabel("Duplicate Sets: 0")
        self.lbl_sum_sets.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.lbl_sum_files = QLabel("Total Duplicate Files: 0")
        self.lbl_sum_files.setStyleSheet("color: #f87171; font-weight: bold; font-size: 13px;")
        self.lbl_sum_savings = QLabel("Reclaimable Space: 0 B")
        self.lbl_sum_savings.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")

        sum_l.addWidget(self.lbl_sum_sets)
        sum_l.addSpacing(20)
        sum_l.addWidget(self.lbl_sum_files)
        sum_l.addSpacing(20)
        sum_l.addWidget(self.lbl_sum_savings)
        sum_l.addStretch()
        layout.addWidget(self.summary_card)

        # Main Splitter (Left: Sets List, Right: Comparison Grid & Actions)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Sets List Widget
        left_w = QFrame()
        left_w.setProperty("class", "Card")
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(12, 12, 12, 12)
        left_l.setSpacing(8)

        left_l.addWidget(QLabel("<b>Duplicate Sets Found:</b>"))

        self.sets_list_widget = QListWidget()
        self.sets_list_widget.itemSelectionChanged.connect(self._on_set_selected)
        left_l.addWidget(self.sets_list_widget)

        splitter.addWidget(left_w)

        # Right: Detail & Action Area
        right_frame = QFrame()
        right_frame.setProperty("class", "Card")
        right_l = QVBoxLayout(right_frame)
        right_l.setSpacing(12)

        # Actions Toolbar
        actions_l = QHBoxLayout()

        actions_l.addWidget(QLabel("Auto-Select Rule:"))
        self.combo_rule = QComboBox()
        self.combo_rule.addItems(["Keep Oldest (Original)", "Keep Newest Copy", "Keep Shortest File Path"])
        actions_l.addWidget(self.combo_rule)

        btn_auto_select = QPushButton("⚡ Apply Rule")
        btn_auto_select.setProperty("class", "SecondaryButton")
        btn_auto_select.clicked.connect(self._apply_auto_select_rule)
        actions_l.addWidget(btn_auto_select)

        actions_l.addStretch()

        self.btn_quarantine = QPushButton("📁 Quarantine Selected")
        self.btn_quarantine.setProperty("class", "SecondaryButton")
        self.btn_quarantine.clicked.connect(self._quarantine_selected)
        actions_l.addWidget(self.btn_quarantine)

        self.btn_delete = QPushButton("🗑 Send Selected to Trash")
        self.btn_delete.setProperty("class", "DangerButton")
        self.btn_delete.setStyleSheet("background-color: #ef4444; color: #ffffff; font-weight: bold;")
        self.btn_delete.clicked.connect(self._delete_selected)
        actions_l.addWidget(self.btn_delete)

        right_l.addLayout(actions_l)

        # Comparison Files Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.files_layout = QVBoxLayout(self.scroll_content)
        self.files_layout.setContentsMargins(8, 8, 8, 8)
        self.files_layout.setSpacing(12)
        self.files_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.scroll_content)
        right_l.addWidget(self.scroll, 1)

        splitter.addWidget(right_frame)
        splitter.setSizes([280, 620])

        layout.addWidget(splitter, 1)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Duplicates")
        if folder and folder not in self.sources:
            self.sources.append(folder)
            self._update_sources_label()

    def _clear_folders(self):
        self.sources.clear()
        self._update_sources_label()

    def _update_sources_label(self):
        if self.sources:
            self.sources_lbl.setText(f"<b>Scan Targets:</b> {', '.join(self.sources)}")
        else:
            default_p = str(Path.home() / "Pictures" / "Organized_Photos")
            self.sources_lbl.setText(f"<b>Scan Targets:</b> Default Output Folder ({default_p})")

    def _run_duplicate_scan(self):
        scan_targets = self.sources or [str(Path.home() / "Pictures" / "Organized_Photos")]

        self.duplicate_sets = self.duplicate_service.scan_directories_for_duplicates(
            sources=scan_targets,
            recursive=self.chk_recursive.isChecked(),
        )

        self.refresh()

    def refresh(self):
        """Refresh duplicate sets list UI while preserving active selection."""
        target_set_id = self.current_set_id
        self.sets_list_widget.clear()

        total_files_cnt = 0
        total_savings_bytes = 0
        select_row = -1

        for idx, dset in enumerate(self.duplicate_sets):
            set_id = dset["set_id"]
            name = dset["sample_name"]
            f_cnt = dset["file_count"]
            savings_str = dset["formatted_savings"]

            total_files_cnt += f_cnt
            total_savings_bytes += dset["potential_savings"]

            item = QListWidgetItem(f"{name}\n({f_cnt} copies | Reclaim {savings_str})")
            item.setData(Qt.UserRole, set_id)
            self.sets_list_widget.addItem(item)

            if target_set_id and set_id == target_set_id:
                select_row = idx

        self.lbl_sum_sets.setText(f"Duplicate Sets: {len(self.duplicate_sets)}")
        self.lbl_sum_files.setText(f"Total Duplicate Files: {total_files_cnt}")
        self.lbl_sum_savings.setText(f"Reclaimable Space: {format_bytes(total_savings_bytes)}")

        if self.sets_list_widget.count() > 0:
            if select_row >= 0:
                self.sets_list_widget.setCurrentRow(select_row)
            else:
                self.sets_list_widget.setCurrentRow(0)

        if not self.duplicate_sets:
            self.current_set_id = None
            self._clear_files_layout()
            lbl_empty = QLabel("🎉 No duplicate image sets found in the selected directories!")
            lbl_empty.setStyleSheet("font-size: 16px; color: #34d399; margin-top: 40px;")
            lbl_empty.setAlignment(Qt.AlignCenter)
            self.files_layout.addWidget(lbl_empty)

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

        for f_info in files:
            p_str = f_info["path"]
            f_path = Path(p_str)
            is_keep = f_info.get("is_recommended_keep", False)

            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            if is_keep:
                card.setStyleSheet("background-color: #064e3b; border: 2px solid #10b981; border-radius: 8px; padding: 10px;")
            else:
                card.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;")

            row_l = QHBoxLayout(card)
            row_l.setContentsMargins(8, 8, 8, 8)
            row_l.setSpacing(14)

            # Thumbnail Image Preview
            if f_path.exists():
                pix = QPixmap(str(f_path)).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(pix)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setFixedSize(110, 110)
                img_lbl.setStyleSheet("border-radius: 6px; background-color: #0f172a;")
                row_l.addWidget(img_lbl)

            # File Metadata Info
            info_l = QVBoxLayout()
            info_l.setSpacing(4)

            name_lbl = QLabel(f"<b>{f_info['filename']}</b>")
            name_lbl.setStyleSheet("font-size: 14px; color: #ffffff;")
            info_l.addWidget(name_lbl)

            path_lbl = QLabel(f"Path: {p_str}")
            path_lbl.setWordWrap(True)
            path_lbl.setToolTip(p_str)
            path_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
            info_l.addWidget(path_lbl)

            meta_lbl = QLabel(f"Size: {f_info['formatted_size']} | Modified: {f_info['formatted_mtime']}")
            meta_lbl.setStyleSheet("font-size: 12px; color: #38bdf8;")
            info_l.addWidget(meta_lbl)

            row_l.addLayout(info_l, 1)

            # Keep vs Remove Selection Controls
            ctrl_l = QVBoxLayout()
            ctrl_l.setAlignment(Qt.AlignCenter)

            rad_keep = QRadioButton("🟢 Keep File")
            rad_keep.setChecked(is_keep)
            rad_keep.setStyleSheet("color: #34d399; font-weight: bold;")
            rad_keep.toggled.connect(lambda checked, fi=f_info: self._toggle_keep(fi, checked))
            ctrl_l.addWidget(rad_keep)

            btn_open = QPushButton("📂 Open Location")
            btn_open.setProperty("class", "SecondaryButton")
            btn_open.setFixedHeight(26)
            btn_open.clicked.connect(lambda _, path=p_str: self._open_file_location(path))
            ctrl_l.addWidget(btn_open)

            row_l.addLayout(ctrl_l)
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

    def _apply_auto_select_rule(self):
        text = self.combo_rule.currentText()
        rule_key = "keep_oldest"
        if "Newest" in text:
            rule_key = "keep_newest"
        elif "Shortest" in text:
            rule_key = "keep_shortest_path"

        self.duplicate_service.apply_auto_select_rule(self.duplicate_sets, rule=rule_key)
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
            f"Are you sure you want to move {len(to_remove)} duplicate files to the Quarantine folder?\n\nOriginal files marked 'Keep File' will remain in place.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            success, err, freed = self.duplicate_service.remove_duplicates(to_remove, mode="quarantine")
            QMessageBox.information(
                self,
                "Quarantine Complete",
                f"Successfully quarantined {success} files.\nReclaimed space: {format_bytes(freed)}.",
            )
            self._run_duplicate_scan()

    def _delete_selected(self):
        to_remove = self._get_all_files_selected_for_removal()
        if not to_remove:
            QMessageBox.information(self, "No Selection", "No duplicate files selected for removal.")
            return

        confirm = QMessageBox.question(
            self,
            "Send Duplicates to Trash",
            f"Are you sure you want to send {len(to_remove)} duplicate files to the Trash / Recycle Bin?\n\nOriginal files marked 'Keep File' will remain untouched.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            success, err, freed = self.duplicate_service.remove_duplicates(to_remove, mode="trash")
            QMessageBox.information(
                self,
                "Duplicates Cleaned",
                f"Successfully sent {success} duplicate files to Trash.\nReclaimed space: {format_bytes(freed)}.",
            )
            self._run_duplicate_scan()
