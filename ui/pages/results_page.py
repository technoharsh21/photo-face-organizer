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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Scan Results")
        header.setProperty("class", "PageHeader")
        layout.addWidget(header)

        # Overview Stats Card
        self.summary_card = QFrame()
        self.summary_card.setProperty("class", "Card")
        sc_layout = QHBoxLayout(self.summary_card)

        self.lbl_processed = QLabel("Processed: 0")
        self.lbl_matched = QLabel("Matched: 0")
        self.lbl_no_match = QLabel("No Match: 0")
        self.lbl_unknown = QLabel("Unknown: 0")
        self.lbl_duration = QLabel("Duration: 0s")

        for l in [self.lbl_processed, self.lbl_matched, self.lbl_no_match, self.lbl_unknown, self.lbl_duration]:
            l.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
            sc_layout.addWidget(l)

        layout.addWidget(self.summary_card)

        # File Audit Reconciliation Summary Card
        self.audit_card = QFrame()
        self.audit_card.setProperty("class", "Card")
        ac_layout = QHBoxLayout(self.audit_card)

        self.lbl_audit_discovered = QLabel("Total Discovered: 0")
        self.lbl_audit_accounted = QLabel("Accounted: 0 / 0 (100%)")
        self.lbl_audit_missed = QLabel("Missed Photos: 0 (Zero Photos Lost)")

        self.lbl_audit_discovered.setStyleSheet("color: #3b82f6; font-weight: bold;")
        self.lbl_audit_accounted.setStyleSheet("color: #10b981; font-weight: bold;")
        self.lbl_audit_missed.setStyleSheet("color: #10b981; font-weight: bold;")

        ac_layout.addWidget(self.lbl_audit_discovered)
        ac_layout.addWidget(self.lbl_audit_accounted)
        ac_layout.addWidget(self.lbl_audit_missed)
        layout.addWidget(self.audit_card)

        # Actions Toolbar
        actions_layout = QHBoxLayout()

        self.btn_open_folder = QPushButton("📂 Open Output Folder")
        self.btn_open_folder.setProperty("class", "PrimaryButton")
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        actions_layout.addWidget(self.btn_open_folder)

        self.btn_correct_match = QPushButton("🛠️ Correct Wrong Match")
        self.btn_correct_match.setProperty("class", "SecondaryButton")
        self.btn_correct_match.clicked.connect(self._correct_wrong_match)
        actions_layout.addWidget(self.btn_correct_match)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Main Splitter (Left: Tree Breakdown, Right: Image Preview Card)
        splitter = QSplitter(Qt.Horizontal)

        # Left Tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Person / Output Folder", "Count / Path"])
        self.tree.setColumnWidth(0, 260)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        left_layout.addWidget(self.tree)

        splitter.addWidget(left_widget)

        # Right Image Preview Panel
        self.preview_frame = QFrame()
        self.preview_frame.setProperty("class", "Card")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setSpacing(12)

        prev_title = QLabel("Photo Preview & Audit Info")
        prev_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        preview_layout.addWidget(prev_title)

        self.img_preview_lbl = QLabel("Select a photo from the left tree to view preview")
        self.img_preview_lbl.setAlignment(Qt.AlignCenter)
        self.img_preview_lbl.setStyleSheet(
            "background-color: #181820; border-radius: 8px; color: #a0a0b0; padding: 20px; font-style: italic;"
        )
        self.img_preview_lbl.setMinimumSize(320, 240)
        preview_layout.addWidget(self.img_preview_lbl)

        self.lbl_photo_info = QLabel("")
        self.lbl_photo_info.setWordWrap(True)
        self.lbl_photo_info.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        preview_layout.addWidget(self.lbl_photo_info)

        preview_layout.addStretch()
        splitter.addWidget(self.preview_frame)
        splitter.setSizes([450, 450])

        layout.addWidget(splitter)

    def load_results(self, summary: dict[str, Any]):
        """Load and display scan summary data."""
        self.summary_data = summary
        self.lbl_processed.setText(f"Processed: {summary.get('processed', 0)}")
        self.lbl_matched.setText(f"Matched: {summary.get('matched', 0)}")
        self.lbl_no_match.setText(f"No Match: {summary.get('no_match', 0)}")
        self.lbl_unknown.setText(f"Unknown: {summary.get('unknown_faces', 0)}")
        self.lbl_duration.setText(f"Duration: {summary.get('duration_seconds', 0)}s")

        # Audit Summary Update
        tot = summary.get("total_files", summary.get("processed", 0))
        acc = summary.get("total_accounted", summary.get("matched", 0) + summary.get("no_match", 0) + summary.get("skipped", 0))
        missed = summary.get("missed_files", max(0, tot - acc))
        pct = summary.get("reconciliation_percent", round((acc / tot) * 100.0, 1) if tot > 0 else 100.0)

        self.lbl_audit_discovered.setText(f"Total Discovered: {tot}")
        self.lbl_audit_accounted.setText(f"Accounted: {acc} / {tot} ({pct}%)")

        if missed == 0:
            self.lbl_audit_missed.setText("Missed Photos: 0 (Zero Photos Lost)")
            self.lbl_audit_missed.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.lbl_audit_missed.setText(f"Missed Photos: {missed} ⚠️")
            self.lbl_audit_missed.setStyleSheet("color: #ef4444; font-weight: bold;")

        self.tree.clear()
        self._clear_preview()

        output_dir_str = summary.get("output_dir")
        if not output_dir_str or not Path(output_dir_str).exists():
            return

        out_path = Path(output_dir_str)
        results_by_person = summary.get("results_by_person", {})
        known_person_names = set(results_by_person.keys())
        known_person_names.add("No Match")

        # Scan output directory for person subfolders
        for person_dir in sorted(out_path.iterdir()):
            if person_dir.is_dir():
                # Show folder if it matches a known profile / No Match or contains files
                files = [f for f in person_dir.iterdir() if f.is_file()]
                if files or person_dir.name in known_person_names:
                    parent_item = QTreeWidgetItem([person_dir.name, f"{len(files)} photos"])
                    parent_item.setData(0, Qt.UserRole, str(person_dir))

                    for f in sorted(files):
                        child_item = QTreeWidgetItem([f.name, str(f)])
                        child_item.setData(0, Qt.UserRole, str(f))
                        parent_item.addChild(child_item)

                    self.tree.addTopLevelItem(parent_item)

        self.tree.expandAll()

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
