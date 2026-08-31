"""
Unknown Faces Management Page Module.

Displays unmatched face clusters, supports inspecting face crops with edge-to-edge covers,
renaming unknown groups, deleting face crops with loading states, and converting groups into new Profiles.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from services.unknown_face_service import UnknownFaceService
from ui.components.flow_layout import FlowLayout


class UnknownFaceCropCover(QWidget):
    """Renders an unknown face crop thumbnail filled edge-to-edge with rounded corners."""

    def __init__(self, image_path: str | None = None, size: int = 120, radius: int = 8, parent=None):
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
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "👤 Face")
        painter.end()


class UnknownGroupListItemWidget(QWidget):
    """Custom rich card for the left Unknown Face Groups sidebar list."""

    def __init__(self, group_name: str, face_count: int, sample_crop_path: str | None):
        super().__init__()
        self.group_name = group_name
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        thumb = UnknownFaceCropCover(sample_crop_path, size=48, radius=8)
        layout.addWidget(thumb)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        name_lbl = QLabel(group_name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        name_lbl.setCursor(Qt.PointingHandCursor)

        sub_lbl = QLabel(f"📦 {face_count} face crop{'s' if face_count != 1 else ''}")
        sub_lbl.setStyleSheet("font-size: 12px; color: #38bdf8; background: transparent; border: none; font-weight: 600;")
        sub_lbl.setCursor(Qt.PointingHandCursor)

        info_col.addWidget(name_lbl)
        info_col.addWidget(sub_lbl)
        layout.addLayout(info_col, 1)


class UnknownFacesClusterWorker(QThread):
    """Background worker for clustering unknown faces without blocking UI."""

    finished_signal = Signal(list)

    def __init__(self, unknown_face_service: UnknownFaceService, threshold: float = 50.0):
        super().__init__()
        self.unknown_face_service = unknown_face_service
        self.threshold = threshold

    def run(self):
        try:
            groups = self.unknown_face_service.group_unknown_faces(threshold=self.threshold)
            self.finished_signal.emit(groups)
        except Exception:
            self.finished_signal.emit([])


class UnknownFacesPage(QWidget):
    """Modern UI Page for inspecting and managing unmatched faces."""

    def __init__(self, unknown_face_service: UnknownFaceService):
        super().__init__()
        self.unknown_face_service = unknown_face_service
        self.groups: list[dict[str, Any]] = []
        self.current_group_id: str | None = None
        self.current_faces: list[dict[str, Any]] = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Header Title & Global Actions
        header_l = QHBoxLayout()
        header_l.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("👤 Unknown Faces Studio")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Inspect unidentified faces. Auto-group similar faces and convert them into new Person Profiles with 1 click.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_title)
        header_l.addLayout(title_box)

        header_l.addStretch()

        btn_cluster = QPushButton("✨ Auto-Group Similar Faces")
        btn_cluster.setProperty("class", "PrimaryButton")
        btn_cluster.setCursor(Qt.PointingHandCursor)
        btn_cluster.setFixedHeight(36)
        btn_cluster.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_cluster.clicked.connect(self._run_clustering)
        header_l.addWidget(btn_cluster)

        btn_clear_all = QPushButton("🧹 Clear All")
        btn_clear_all.setProperty("class", "DangerButton")
        btn_clear_all.setCursor(Qt.PointingHandCursor)
        btn_clear_all.setFixedHeight(36)
        btn_clear_all.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        btn_clear_all.clicked.connect(self._clear_all_unknown_faces)
        header_l.addWidget(btn_clear_all)

        layout.addLayout(header_l)

        # 2. Hero Summary Bar
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 10px 16px;")
        sum_l = QHBoxLayout(self.summary_card)
        sum_l.setContentsMargins(10, 6, 10, 6)
        sum_l.setSpacing(16)

        self.lbl_sum_groups = QLabel("👥 Unknown Groups: 0")
        self.lbl_sum_groups.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.lbl_sum_faces = QLabel("📷 Stored Face Crops: 0")
        self.lbl_sum_faces.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 13px;")
        self.lbl_sum_engine = QLabel("🧠 Model: ArcFace (512-d)")
        self.lbl_sum_engine.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")

        sum_l.addWidget(self.lbl_sum_groups)
        sum_l.addWidget(self.lbl_sum_faces)
        sum_l.addWidget(self.lbl_sum_engine)
        sum_l.addStretch()
        layout.addWidget(self.summary_card)

        # 3. Main Splitter (Left: Groups List, Right: Group Faces Grid)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Groups List (Enlarged width so no empty column on the right)
        left_w = QFrame()
        left_w.setProperty("class", "Card")
        left_w.setMinimumWidth(340)
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(14, 14, 14, 14)
        left_l.setSpacing(10)

        left_hdr_row = QHBoxLayout()
        left_hdr = QLabel("<b>Unknown Face Clusters</b>")
        left_hdr.setStyleSheet("font-size: 14px; color: #ffffff;")
        self.lbl_group_count = QLabel("0 Groups")
        self.lbl_group_count.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        left_hdr_row.addWidget(left_hdr)
        left_hdr_row.addStretch()
        left_hdr_row.addWidget(self.lbl_group_count)
        left_l.addLayout(left_hdr_row)

        self.txt_filter_groups = QLineEdit()
        self.txt_filter_groups.setPlaceholderText("🔍 Filter unknown groups...")
        self.txt_filter_groups.setStyleSheet(
            "QLineEdit { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 8px 12px; font-size: 12px; color: #ffffff; }"
            "QLineEdit:focus { border: 2px solid #67e8f9; background-color: #131d33; }"
        )
        self.txt_filter_groups.textChanged.connect(self._filter_groups_list)
        left_l.addWidget(self.txt_filter_groups)

        self.groups_list = QListWidget()
        self.groups_list.setCursor(Qt.PointingHandCursor)
        self.groups_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.groups_list.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; padding: 4px; outline: 0px; }"
            "QListWidget::item { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 6px; padding: 2px; }"
            "QListWidget::item:hover { background-color: #162238; border: 1px solid #38bdf8; }"
            "QListWidget::item:selected { background-color: #1e293b; border: 2px solid #38bdf8; }"
        )
        self.groups_list.itemSelectionChanged.connect(self._on_group_selected)
        left_l.addWidget(self.groups_list, 1)

        splitter.addWidget(left_w)

        # Right Detail Area
        right_frame = QFrame()
        right_frame.setProperty("class", "Card")
        right_l = QVBoxLayout(right_frame)
        right_l.setContentsMargins(16, 16, 16, 16)
        right_l.setSpacing(14)

        self.group_title_lbl = QLabel("Select an Unknown Face Group")
        self.group_title_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        right_l.addWidget(self.group_title_lbl)

        # Actions Toolbar — wraps to next line on narrow windows so button text never clips
        actions_l = FlowLayout(h_spacing=12, v_spacing=8)

        self.btn_convert = QPushButton("⭐ Convert to Profile")
        self.btn_convert.setCursor(Qt.PointingHandCursor)
        self.btn_convert.setFixedHeight(36)
        self.btn_convert.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_convert.clicked.connect(self._convert_group_to_profile)
        actions_l.addWidget(self.btn_convert)

        self.btn_add_to_existing = QPushButton("➕ Add to Profile")
        self.btn_add_to_existing.setCursor(Qt.PointingHandCursor)
        self.btn_add_to_existing.setFixedHeight(36)
        self.btn_add_to_existing.setStyleSheet(
            "QPushButton { background-color: #0284c7; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #0369a1; }"
            "QPushButton:hover { background-color: #0369a1; }"
        )
        self.btn_add_to_existing.clicked.connect(self._add_group_to_existing_profile)
        actions_l.addWidget(self.btn_add_to_existing)

        self.btn_rename_grp = QPushButton("✏️ Rename Group")
        self.btn_rename_grp.setCursor(Qt.PointingHandCursor)
        self.btn_rename_grp.setFixedHeight(36)
        self.btn_rename_grp.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_rename_grp.clicked.connect(self._rename_group)
        actions_l.addWidget(self.btn_rename_grp)

        self.btn_delete_grp = QPushButton("🗑️ Delete Group")
        self.btn_delete_grp.setCursor(Qt.PointingHandCursor)
        self.btn_delete_grp.setFixedHeight(36)
        self.btn_delete_grp.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        self.btn_delete_grp.clicked.connect(self._delete_group)
        actions_l.addWidget(self.btn_delete_grp)

        right_l.addLayout(actions_l)

        # Faces scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.scroll_content)
        right_l.addWidget(self.scroll, 1)

        splitter.addWidget(right_frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)
        self.refresh()

    def refresh(self):
        """Refresh unknown face groups list."""
        self._run_clustering()

    def _run_clustering(self):
        target_group_id = self.current_group_id
        self.group_title_lbl.setText("⏳ Analyzing & grouping unknown faces...")

        self.cluster_worker = UnknownFacesClusterWorker(self.unknown_face_service, threshold=50.0)

        def on_clustered(groups: list[dict[str, Any]]):
            self.groups = groups
            self.groups_list.blockSignals(True)
            self.groups_list.clear()

            total_crops = 0
            select_row = -1

            for idx, g in enumerate(self.groups):
                g_id = g.get("group_id")
                g_name = g.get("group_name", "Unknown Group")
                faces = g.get("faces", [])
                faces_cnt = len(faces)
                total_crops += faces_cnt

                first_crop = faces[0].get("crop_path") if faces else None

                item = QListWidgetItem()
                item.setData(Qt.UserRole, g_id)
                item.setSizeHint(QSize(220, 68))
                self.groups_list.addItem(item)

                widget = UnknownGroupListItemWidget(
                    group_name=g_name,
                    face_count=faces_cnt,
                    sample_crop_path=first_crop,
                )
                self.groups_list.setItemWidget(item, widget)

                if target_group_id and g_id == target_group_id:
                    select_row = idx

            self.groups_list.blockSignals(False)

            self.lbl_sum_groups.setText(f"👥 Unknown Groups: {len(self.groups)}")
            self.lbl_sum_faces.setText(f"📷 Stored Face Crops: {total_crops}")
            self.lbl_group_count.setText(f"{len(self.groups)} Group{'s' if len(self.groups) != 1 else ''}")

            if self.groups_list.count() > 0:
                if select_row >= 0:
                    self.groups_list.setCurrentRow(select_row)
                else:
                    self.groups_list.setCurrentRow(0)
                items = self.groups_list.selectedItems()
                if items:
                    active_id = items[0].data(Qt.UserRole)
                    grp = next((g for g in self.groups if g.get("group_id") == active_id), None)
                    if grp:
                        self.group_title_lbl.setText(f"Group: {grp.get('group_name')} ({len(grp.get('faces', []))} faces)")
                        self._display_faces(grp.get("faces", []))
            else:
                self.current_group_id = None
                self.group_title_lbl.setText("No unknown faces stored.")
                self._clear_faces_grid()

        self.cluster_worker.finished_signal.connect(on_clustered)
        self.cluster_worker.start()

    def _filter_groups_list(self, query: str):
        q = query.strip().lower()
        for i in range(self.groups_list.count()):
            item = self.groups_list.item(i)
            w = self.groups_list.itemWidget(item)
            if isinstance(w, UnknownGroupListItemWidget):
                item.setHidden(q not in w.group_name.lower())

    def _on_group_selected(self):
        items = self.groups_list.selectedItems()
        if not items:
            self.current_group_id = None
            self.group_title_lbl.setText("Select an Unknown Face Group")
            self._clear_faces_grid()
            return

        g_id = items[0].data(Qt.UserRole)
        self.current_group_id = g_id

        grp = next((g for g in self.groups if g.get("group_id") == g_id), None)
        if grp:
            self.group_title_lbl.setText(f"Group: {grp.get('group_name')} ({len(grp.get('faces', []))} faces)")
            self._display_faces(grp.get("faces", []))

    def _clear_faces_grid(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "current_faces") and self.current_faces:
            self._display_faces(self.current_faces)

    def _display_faces(self, faces: list[dict[str, Any]]):
        self._clear_faces_grid()
        self.current_faces = faces

        viewport_w = self.scroll.viewport().width()
        available_w = max(340, viewport_w - 24)
        target_w = 145
        spacing = 14
        cols = max(2, (available_w + spacing) // (target_w + spacing))
        actual_card_w = (available_w - (cols - 1) * spacing) // cols
        thumb_size = max(100, actual_card_w - 20)

        for idx, f in enumerate(faces):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; padding: 8px; }"
                "QFrame:hover { border: 1px solid #38bdf8; }"
            )
            card.setFixedWidth(actual_card_w)
            l = QVBoxLayout(card)
            l.setContentsMargins(8, 8, 8, 8)
            l.setSpacing(6)

            crop_path = f.get("crop_path")
            thumb = UnknownFaceCropCover(crop_path, size=thumb_size, radius=8)
            l.addWidget(thumb, 0, Qt.AlignCenter)

            src_path_str = f.get("source_photo_path", "")
            src_file = Path(src_path_str).name if src_path_str else "Photo"
            src_lbl = QLabel(f"From: {src_file}")
            src_lbl.setWordWrap(True)
            src_lbl.setToolTip(src_path_str)
            src_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1;")
            l.addWidget(src_lbl)

            btn_del = QPushButton("🗑️ Delete")
            btn_del.setProperty("class", "DangerButton")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedHeight(30)
            btn_del.setStyleSheet(
                "QPushButton { font-size: 12px; padding: 0 10px; background-color: #dc2626; color: #ffffff; border: none; border-radius: 6px; font-weight: 700; }"
                "QPushButton:hover { background-color: #b91c1c; }"
            )
            f_id = f.get("id")
            btn_del.clicked.connect(lambda _, u_id=f_id, btn=btn_del: self._delete_face(u_id, btn))
            l.addWidget(btn_del)

            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

    def _rename_group(self):
        if not self.current_group_id:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Group", "Enter Group Name:")
        if ok and new_name.strip():
            self.unknown_face_service.rename_group(self.current_group_id, new_name.strip())
            self.refresh()

    def _convert_group_to_profile(self):
        if not self.current_group_id:
            return

        grp = next((g for g in self.groups if g.get("group_id") == self.current_group_id), None)
        default_name = grp.get("group_name", "New Person") if grp else "New Person"

        name, ok = QInputDialog.getText(self, "Convert Group to Profile", "Enter New Profile Name:", text=default_name)
        if ok and name.strip():
            try:
                profile = self.unknown_face_service.convert_group_to_profile(self.current_group_id, name.strip())
                if profile:
                    QMessageBox.information(self, "Success", f"Created Profile '{profile['name']}' from unknown face group.")
                    self.refresh()
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Profile Already Exists",
                    f"A profile named '{name.strip()}' already exists.\n\nPlease choose a different name or use 'Add to Profile'.",
                )

    def _add_group_to_existing_profile(self):
        if not self.current_group_id:
            return

        profiles = self.unknown_face_service.profile_service.list_profiles()
        if not profiles:
            QMessageBox.warning(self, "No Profiles Found", "No person profiles exist yet. Please create a profile first.")
            return

        items = [f"{p['name']} ({len(p.get('references', []))} refs)" for p in profiles]
        item, ok = QInputDialog.getItem(self, "Add to Existing Profile", "Select Target Person Profile:", items, 0, False)
        if ok and item:
            idx = items.index(item)
            target_p = profiles[idx]
            updated_p = self.unknown_face_service.add_group_to_existing_profile(self.current_group_id, target_p["id"])
            if updated_p:
                QMessageBox.information(self, "Success", f"Successfully added unknown face group to profile '{updated_p['name']}'.")
                self.refresh()

    def _delete_face(self, unknown_id: str, btn: QPushButton | None = None):
        if not unknown_id:
            return
        if btn:
            btn.setEnabled(False)
            btn.setText("⏳")
        self.unknown_face_service.delete_unknown_face(unknown_id)
        self.refresh()

    def _delete_group(self):
        if not self.current_group_id:
            return

        confirm = QMessageBox.question(
            self,
            "Delete Unknown Face Group",
            "Are you sure you want to delete this entire group of unknown faces?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.unknown_face_service.delete_group(self.current_group_id)
            self.current_group_id = None
            self.refresh()

    def _clear_all_unknown_faces(self):
        confirm = QMessageBox.question(
            self,
            "Clear All Unknown Faces",
            "Are you sure you want to delete all stored unknown face records?\n\nThis will clear the unknown faces list completely.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            cnt = self.unknown_face_service.delete_all_unknown_faces()
            self.current_group_id = None
            self.refresh()
            QMessageBox.information(self, "Cleared", f"Cleared {cnt} unknown face records.")
