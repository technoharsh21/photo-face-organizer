"""
Results Page Module.

Requirements #27 & #28:
Displays detailed scan summary, results breakdown by person, live photo preview panel,
folder opening button, and wrong match correction interface.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.image_loader import load_image
from services.output_service import OutputService
from services.profile_service import ProfileService
from ui.components.wrong_match_dialog import WrongMatchDialog


class ResultsPage(QWidget):
    """Scan Results Page with live image preview panel and wrong match correction."""

    def __init__(self, profile_service: ProfileService, output_service: OutputService):
        super().__init__()
        self.profile_service = profile_service
        self.output_service = output_service
        self.summary_data: dict[str, Any] | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Executive Scan Summary & Audit Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 16px;")
        sc_vlayout = QVBoxLayout(self.summary_card)
        sc_vlayout.setSpacing(12)

        # Top row stats metrics
        stats_box = QHBoxLayout()
        stats_box.setSpacing(12)

        self.c_processed = self._create_metric_badge("PROCESSED", "0", "#ffffff")
        self.c_matched = self._create_metric_badge("MATCHED", "0", "#10b981")
        self.c_no_match = self._create_metric_badge("NO MATCH", "0", "#f59e0b")
        self.c_unknown = self._create_metric_badge("UNKNOWN", "0", "#ec4899")
        self.c_duration = self._create_metric_badge("DURATION", "0s", "#38bdf8")

        stats_box.addWidget(self.c_processed["frame"])
        stats_box.addWidget(self.c_matched["frame"])
        stats_box.addWidget(self.c_no_match["frame"])
        stats_box.addWidget(self.c_unknown["frame"])
        stats_box.addWidget(self.c_duration["frame"])

        sc_vlayout.addLayout(stats_box)

        # Audit & Actions Row
        audit_row = QHBoxLayout()
        audit_row.setSpacing(8)

        self.lbl_audit_status = QLabel("<b>Audit:</b> Accounted: 0 / 0 (100%) • 🟢 Zero Photos Lost")
        self.lbl_audit_status.setStyleSheet("color: #10b981; font-size: 12px;")
        audit_row.addWidget(self.lbl_audit_status)

        audit_row.addStretch()

        self.btn_skipped_details = QPushButton("ℹ️ Skipped Details")
        self.btn_skipped_details.setProperty("class", "SecondaryButton")
        self.btn_skipped_details.setCursor(Qt.PointingHandCursor)
        self.btn_skipped_details.setToolTip("View details for any skipped or unreadable files.")
        self.btn_skipped_details.clicked.connect(self._open_skipped_details_dialog)
        audit_row.addWidget(self.btn_skipped_details)

        self.btn_correct_match = QPushButton("🛠️ Correct Match")
        self.btn_correct_match.setProperty("class", "SecondaryButton")
        self.btn_correct_match.setCursor(Qt.PointingHandCursor)
        self.btn_correct_match.setToolTip("Reassign a photo to a different person.")
        self.btn_correct_match.clicked.connect(self._correct_wrong_match)
        audit_row.addWidget(self.btn_correct_match)

        self.btn_open_folder = QPushButton("📂 Open Output Folder")
        self.btn_open_folder.setProperty("class", "PrimaryButton")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        audit_row.addWidget(self.btn_open_folder)

        sc_vlayout.addLayout(audit_row)
        layout.addWidget(self.summary_card)

        # 2. Main Splitter (Left: Tree Breakdown, Right: Image Preview Card)
        splitter = QSplitter(Qt.Horizontal)

        # Left Tree Container Card
        left_widget = QFrame()
        left_widget.setProperty("class", "Card")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)

        left_hdr = QLabel("<b>Person Output Folders & Matched Photos</b>")
        left_hdr.setStyleSheet("font-size: 13px; color: #ffffff;")
        left_layout.addWidget(left_hdr)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Person / Output Folder", "Count / Path"])
        self.tree.setColumnWidth(0, 260)
        self.tree.setStyleSheet(
            "QTreeWidget { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; color: #f8fafc; font-size: 13px; }"
            "QTreeWidget::item { padding: 6px; border-bottom: 1px solid #1e293b; }"
            "QTreeWidget::item:selected { background-color: #0284c7; color: #ffffff; font-weight: bold; }"
            "QHeaderView::section { background-color: #1e293b; color: #38bdf8; font-weight: bold; padding: 6px; border: none; }"
        )
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        left_layout.addWidget(self.tree, 1)

        splitter.addWidget(left_widget)

        # Right Image Preview Panel Card
        self.preview_frame = QFrame()
        self.preview_frame.setProperty("class", "Card")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)

        prev_title = QLabel("<b>Photo Preview & Match Details</b>")
        prev_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        preview_layout.addWidget(prev_title)

        self.img_preview_lbl = QLabel("Select a photo from the left tree to view preview")
        self.img_preview_lbl.setAlignment(Qt.AlignCenter)
        self.img_preview_lbl.setStyleSheet(
            "background-color: #0f172a; border: 1px dashed #334155; border-radius: 8px; color: #94a3b8; padding: 20px; font-size: 12px;"
        )
        preview_layout.addWidget(self.img_preview_lbl, 1)

        self.lbl_photo_info = QLabel("")
        self.lbl_photo_info.setWordWrap(True)
        self.lbl_photo_info.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        preview_layout.addWidget(self.lbl_photo_info)

        splitter.addWidget(self.preview_frame)
        splitter.setSizes([380, 520])

        layout.addWidget(splitter, 1)

    def _create_metric_badge(self, title: str, val: str, color: str) -> dict[str, Any]:
        frame = QFrame()
        frame.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 8px 14px;")
        l = QVBoxLayout(frame)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 0.5px;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color};")

        l.addWidget(lbl_t)
        l.addWidget(lbl_v)

        return {"frame": frame, "val": lbl_v}

    def load_results(self, summary: dict[str, Any]):
        """Load and display scan summary data."""
        self.summary_data = summary
        self.c_processed["val"].setText(f"{summary.get('processed', 0)}")
        self.c_matched["val"].setText(f"{summary.get('matched', 0)}")
        self.c_no_match["val"].setText(f"{summary.get('no_match', 0)}")
        self.c_unknown["val"].setText(f"{summary.get('unknown_faces', 0)}")
        self.c_duration["val"].setText(f"{summary.get('duration_seconds', 0)}s")

        # Audit Summary Update
        tot = summary.get("total_files", summary.get("processed", 0))
        acc = summary.get("total_accounted", summary.get("matched", 0) + summary.get("no_match", 0) + summary.get("skipped", 0))
        missed = summary.get("missed_files", max(0, tot - acc))
        pct = summary.get("reconciliation_percent", round((acc / tot) * 100.0, 1) if tot > 0 else 100.0)

        if missed == 0:
            self.lbl_audit_status.setText(f"<b>File Reconciliation Audit:</b> Accounted: {acc} / {tot} ({pct}%) • 🟢 Zero Photos Lost")
            self.lbl_audit_status.setStyleSheet("color: #10b981; font-size: 12px;")
        else:
            self.lbl_audit_status.setText(f"<b>File Reconciliation Audit:</b> Accounted: {acc} / {tot} ({pct}%) • ⚠️ {missed} Missed Photos")
            self.lbl_audit_status.setStyleSheet("color: #ef4444; font-size: 12px;")

        # Populate the person folders + matched photos tree
        self._populate_results_tree(summary)

    def _populate_results_tree(self, summary: dict[str, Any]):
        """Build the person folder tree from the output directory after scan completes."""
        self.tree.clear()
        self._clear_preview()

        output_dir_str = summary.get("output_dir")
        if not output_dir_str or not Path(output_dir_str).exists():
            # No output folder yet — show a helpful placeholder message
            placeholder = QTreeWidgetItem(["No output folder found", ""])
            placeholder.setDisabled(True)
            self.tree.addTopLevelItem(placeholder)
            return

        out_path = Path(output_dir_str)
        results_by_person = summary.get("results_by_person", {})
        known_person_names = set(results_by_person.keys())
        known_person_names.add("No Match")

        found_any = False
        # Scan output directory for person subfolders
        for person_dir in sorted(out_path.iterdir()):
            if person_dir.is_dir():
                files = [f for f in person_dir.iterdir() if f.is_file()]
                if files or person_dir.name in known_person_names:
                    found_any = True
                    photo_count = len(files)
                    parent_item = QTreeWidgetItem([
                        f"📁 {person_dir.name}",
                        f"{photo_count} photo{'s' if photo_count != 1 else ''}",
                    ])
                    parent_item.setData(0, Qt.UserRole, str(person_dir))

                    for f in sorted(files):
                        child_item = QTreeWidgetItem([f.name, str(f)])
                        child_item.setData(0, Qt.UserRole, str(f))
                        parent_item.addChild(child_item)

                    self.tree.addTopLevelItem(parent_item)

        if not found_any:
            placeholder = QTreeWidgetItem(["No matched photos found", "0 photos"])
            placeholder.setDisabled(True)
            self.tree.addTopLevelItem(placeholder)

        self.tree.expandAll()

    def _open_skipped_details_dialog(self):
        """Show dialog with details of skipped/unreadable files."""
        if not self.summary_data:
            QMessageBox.information(self, "No Scan Data", "No scan summary data available.")
            return
        from ui.components.skipped_files_dialog import SkippedFilesDialog
        dlg = SkippedFilesDialog(self, self.summary_data)
        dlg.exec()

    def _clear_preview(self):

        self.img_preview_lbl.setPixmap(QPixmap())
        self.img_preview_lbl.setText("Select a photo from the left tree to view preview")
        self.lbl_photo_info.setText("")

    def _on_tree_selection_changed(self):
        item = self.tree.currentItem()
        if not item or not item.parent():
            # Selected a parent person folder
            if item:
                folder_name = item.text(0)
                photo_cnt = item.text(1)
                self.img_preview_lbl.setPixmap(QPixmap())
                self.img_preview_lbl.setText(f"Folder Selected: {folder_name}\n({photo_cnt})")
                self.lbl_photo_info.setText(f"Folder Path: {item.data(0, Qt.UserRole)}")
            else:
                self._clear_preview()
            return

        # Selected a photo file item
        file_path_str = item.data(0, Qt.UserRole)
        if not file_path_str:
            self._clear_preview()
            return

        file_path = Path(file_path_str)
        if not file_path.exists():
            self.img_preview_lbl.setPixmap(QPixmap())
            self.img_preview_lbl.setText(f"File not found:\n{file_path.name}")
            self.lbl_photo_info.setText(str(file_path))
            return

        # Load image preview using load_image
        pil_img, err = load_image(file_path)
        if pil_img:
            # Convert PIL Image to QPixmap
            rgb_img = pil_img.convert("RGB")
            data = rgb_img.tobytes("raw", "RGB")
            from PySide6.QtGui import QImage
            qimg = QImage(data, rgb_img.width, rgb_img.height, rgb_img.width * 3, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(320, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.img_preview_lbl.setPixmap(pix)
            self.img_preview_lbl.setText("")
        else:
            self.img_preview_lbl.setPixmap(QPixmap())
            self.img_preview_lbl.setText(f"Preview unavailable:\n{err or 'Unreadable format'}")

        person_folder = item.parent().text(0)
        file_size_kb = round(file_path.stat().st_size / 1024, 1)
        self.lbl_photo_info.setText(
            f"<b>Photo:</b> {file_path.name}<br>"
            f"<b>Match Group:</b> {person_folder}<br>"
            f"<b>Size:</b> {file_size_kb} KB<br>"
            f"<b>Path:</b> {file_path}"
        )

    def _open_output_folder(self):
        if not self.summary_data:
            QMessageBox.warning(self, "No Scan Results", "No scan results available yet.")
            return
        out_dir = self.summary_data.get("output_dir")
        if not out_dir:
            QMessageBox.warning(self, "No Output Folder", "No output directory recorded for this scan.")
            return

        target_path = Path(out_dir).resolve()
        try:
            target_path.mkdir(parents=True, exist_ok=True)
            url = QUrl.fromLocalFile(str(target_path))
            opened = QDesktopServices.openUrl(url)
            if not opened:
                import os
                import subprocess
                import sys

                if sys.platform == "linux":
                    subprocess.Popen(["xdg-open", str(target_path)])
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target_path)])
                elif sys.platform == "win32":
                    os.startfile(str(target_path))
        except Exception as e:
            QMessageBox.warning(self, "Error Opening Folder", f"Failed to open output directory: {e}")

    def _correct_wrong_match(self):
        if not self.summary_data:
            QMessageBox.warning(self, "No Scan Results", "No scan results available yet.")
            return

        item = self.tree.currentItem()
        if not item or not item.parent():
            QMessageBox.warning(
                self,
                "Select Photo File",
                "Please click and select a specific photo file inside a person folder to correct.",
            )
            return

        file_path_str = item.data(0, Qt.UserRole)
        if not file_path_str:
            return

        file_path = Path(file_path_str)
        if not file_path.exists():
            QMessageBox.warning(self, "File Not Found", f"Photo file no longer exists at path:\n{file_path}")
            return

        current_folder = item.parent().text(0)
        profiles = self.profile_service.list_profiles()

        dlg = WrongMatchDialog(self, file_path, current_folder, profiles)
        if dlg.exec() == WrongMatchDialog.Accepted:
            dest_type = dlg.target_destination
            target_profile_name = dlg.selected_profile_name

            out_dir_str = self.summary_data.get("output_dir")
            if not out_dir_str:
                return
            out_dir = Path(out_dir_str)

            if dest_type == "No Match":
                dest_folder = out_dir / "No Match"
                folder_key = "No Match"
            else:
                if not target_profile_name:
                    return
                dest_folder = out_dir / target_profile_name
                folder_key = target_profile_name

            # Copy file to new destination
            _success, _target_path, status = self.output_service.copy_photo_to_destination(
                file_path, dest_folder, folder_key=folder_key
            )

            if status == "DUPLICATE_SKIPPED":
                QMessageBox.information(
                    self,
                    "Duplicate Detected",
                    f"Photo already exists in '{folder_key}' target folder.",
                )

            # Remove incorrect output copy (MANDATE: original source file is unchanged)
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                QMessageBox.warning(self, "Error Removing File", f"Failed to remove incorrect copy: {e}")

            QMessageBox.information(self, "Correction Complete", "Photo match corrected successfully.")
            self.load_results(self.summary_data)
