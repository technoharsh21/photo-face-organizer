"""
Results Page Module.

Displays detailed scan summary metrics, reconciliation audit, interactive person output folder tree,
live high-resolution image preview, quick match correction, and direct folder explorer actions.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.image_loader import load_image
from services.output_service import OutputService
from services.profile_service import ProfileService
from ui.components.flow_layout import FlowLayout
from ui.components.wrong_match_dialog import WrongMatchDialog


class ResultsImageCover(QWidget):
    """Renders a photo preview filled edge-to-edge with antialiased rounded corners and zero black letterbox bars."""

    def __init__(self, image_path: str | None = None, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.pixmap: QPixmap | None = None
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if image_path:
            self.set_image_path(image_path)

    def set_image_path(self, image_path: str | None):
        self.image_path = image_path
        self.pixmap = None
        if image_path and Path(image_path).exists():
            try:
                pil_img, _ = load_image(Path(image_path))
                if pil_img:
                    rgb_img = pil_img.convert("RGB")
                    data = rgb_img.tobytes("raw", "RGB")
                    from PySide6.QtGui import QImage
                    qimg = QImage(data, rgb_img.width, rgb_img.height, rgb_img.width * 3, QImage.Format_RGB888)
                    self.pixmap = QPixmap.fromImage(qimg)
            except Exception:
                self.pixmap = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w = self.width()
        h = self.height()
        radius = 10

        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, radius, radius)
            painter.setClipPath(path)

            # Dark sleek background
            painter.setBrush(QColor("#080c14"))
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, w, h)

            x_off = (w - scaled.width()) // 2
            y_off = (h - scaled.height()) // 2
            painter.drawPixmap(x_off, y_off, scaled)
        else:
            painter.setBrush(QColor("#080c14"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, radius, radius)
            painter.setPen(QColor("#64748b"))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "Select a photo from the tree to view preview")
        painter.end()


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

        # 1. Header Title & Top Actions
        header_l = QHBoxLayout()
        header_l.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("📊 Scan Results & Output Inspector")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Review processed photos, verify audit statistics, correct matches, and open person destination folders.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_title)
        header_l.addLayout(title_box)

        header_l.addStretch()

        # Button cluster wraps on narrow windows so text never clips
        header_btns = FlowLayout(h_spacing=8, v_spacing=8)

        self.btn_skipped_details = QPushButton("ℹ️ Skipped Details")
        self.btn_skipped_details.setProperty("class", "SecondaryButton")
        self.btn_skipped_details.setCursor(Qt.PointingHandCursor)
        self.btn_skipped_details.setFixedHeight(36)
        self.btn_skipped_details.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; min-height: 36px; max-height: 36px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_skipped_details.clicked.connect(self._open_skipped_details_dialog)
        header_btns.addWidget(self.btn_skipped_details)

        self.btn_correct_match = QPushButton("🛠️ Correct Match")
        self.btn_correct_match.setProperty("class", "SecondaryButton")
        self.btn_correct_match.setCursor(Qt.PointingHandCursor)
        self.btn_correct_match.setFixedHeight(36)
        self.btn_correct_match.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; min-height: 36px; max-height: 36px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_correct_match.clicked.connect(self._correct_wrong_match)
        header_btns.addWidget(self.btn_correct_match)

        self.btn_open_folder = QPushButton("📂 Open Output Folder")
        self.btn_open_folder.setProperty("class", "PrimaryButton")
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setFixedHeight(36)
        self.btn_open_folder.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; min-height: 36px; max-height: 36px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        header_btns.addWidget(self.btn_open_folder)

        header_l.addLayout(header_btns)

        layout.addLayout(header_l)

        # 2. Executive Scan Summary & Audit Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 12px; padding: 14px;")
        sc_vlayout = QVBoxLayout(self.summary_card)
        sc_vlayout.setSpacing(10)

        # 5 Sleek Stat Badges
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

        # Audit Row
        self.lbl_audit_status = QLabel("<b>Audit:</b> Accounted: 0 / 0 (100%) • 🟢 Zero Photos Lost")
        self.lbl_audit_status.setStyleSheet("color: #10b981; font-size: 12px;")
        sc_vlayout.addWidget(self.lbl_audit_status)

        layout.addWidget(self.summary_card)

        # 3. Main Splitter (Left: Tree Breakdown, Right: Image Preview Card)
        splitter = QSplitter(Qt.Horizontal)

        # Left Tree Container Card
        left_widget = QFrame()
        left_widget.setProperty("class", "Card")
        left_widget.setMinimumWidth(320)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        left_hdr = QLabel("<b>Person Output Folders & Matched Photos</b>")
        left_hdr.setStyleSheet("font-size: 13px; color: #ffffff;")
        left_layout.addWidget(left_hdr)

        # Search Filter
        self.txt_filter_tree = QLineEdit()
        self.txt_filter_tree.setPlaceholderText("🔍 Filter folders & photos...")
        self.txt_filter_tree.setStyleSheet(
            "QLineEdit { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 6px 12px; font-size: 12px; color: #ffffff; font-weight: 600; }"
            "QLineEdit:focus { border: 2px solid #67e8f9; background-color: #131d33; }"
        )
        self.txt_filter_tree.textChanged.connect(self._filter_tree)
        left_layout.addWidget(self.txt_filter_tree)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Person / Output Folder", "Count / Path"])
        self.tree.setColumnWidth(0, 240)
        self.tree.setStyleSheet(
            "QTreeWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; color: #f8fafc; font-size: 13px; outline: 0px; padding: 4px; }"
            "QTreeWidget::item { padding: 6px; border-bottom: 1px solid #1e293b; border-radius: 6px; margin-bottom: 2px; }"
            "QTreeWidget::item:hover { background-color: #131d33; }"
            "QTreeWidget::item:selected { background-color: #0284c7; color: #ffffff; font-weight: bold; }"
            "QHeaderView::section { background-color: #0f172a; color: #38bdf8; font-weight: bold; padding: 6px; border: none; }"
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

        # Image cover widget
        self.img_cover = ResultsImageCover()
        preview_layout.addWidget(self.img_cover, 1)

        # Photo details info card
        self.info_card = QFrame()
        self.info_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        ic_layout = QVBoxLayout(self.info_card)
        ic_layout.setSpacing(4)

        self.lbl_photo_info = QLabel("Select a photo from the left tree to inspect details")
        self.lbl_photo_info.setWordWrap(True)
        self.lbl_photo_info.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        ic_layout.addWidget(self.lbl_photo_info)

        preview_layout.addWidget(self.info_card)

        splitter.addWidget(self.preview_frame)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

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
            placeholder = QTreeWidgetItem(["No output folder found", ""])
            placeholder.setDisabled(True)
            self.tree.addTopLevelItem(placeholder)
            return

        out_path = Path(output_dir_str)
        results_by_person = summary.get("results_by_person", {})
        known_person_names = set(results_by_person.keys())
        known_person_names.add("No Match")

        found_any = False
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

    def _filter_tree(self, query: str):
        q = query.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            parent_match = q in parent.text(0).lower()
            visible_children = 0
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_match = q in child.text(0).lower() or q in child.text(1).lower()
                child.setHidden(not (parent_match or child_match))
                if not child.isHidden():
                    visible_children += 1
            parent.setHidden(not (parent_match or visible_children > 0))

    def _open_skipped_details_dialog(self):
        """Show dialog with details of skipped/unreadable files."""
        if not self.summary_data:
            QMessageBox.information(self, "No Scan Data", "No scan summary data available.")
            return
        from ui.components.skipped_files_dialog import SkippedFilesDialog
        dlg = SkippedFilesDialog(self, self.summary_data)
        dlg.exec()

    def _clear_preview(self):
        self.img_cover.set_image_path(None)
        self.lbl_photo_info.setText("Select a photo from the left tree to inspect details")

    def _on_tree_selection_changed(self):
        item = self.tree.currentItem()
        if not item or not item.parent():
            if item:
                folder_name = item.text(0)
                photo_cnt = item.text(1)
                self.img_cover.set_image_path(None)
                self.lbl_photo_info.setText(f"<b>Folder Selected:</b> {folder_name} ({photo_cnt})<br><b>Path:</b> {item.data(0, Qt.UserRole)}")
            else:
                self._clear_preview()
            return

        file_path_str = item.data(0, Qt.UserRole)
        if not file_path_str:
            self._clear_preview()
            return

        file_path = Path(file_path_str)
        if not file_path.exists():
            self.img_cover.set_image_path(None)
            self.lbl_photo_info.setText(f"File not found: {file_path.name}")
            return

        self.img_cover.set_image_path(str(file_path))

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
                import os, subprocess, sys
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

            _success, _target_path, status = self.output_service.copy_photo_to_destination(
                file_path, dest_folder, folder_key=folder_key
            )

            if status == "DUPLICATE_SKIPPED":
                QMessageBox.information(
                    self,
                    "Duplicate Detected",
                    f"Photo already exists in '{folder_key}' target folder.",
                )

            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                QMessageBox.warning(self, "Error Removing File", f"Failed to remove incorrect copy: {e}")

            QMessageBox.information(self, "Correction Complete", "Photo match corrected successfully.")
            self.load_results(self.summary_data)
