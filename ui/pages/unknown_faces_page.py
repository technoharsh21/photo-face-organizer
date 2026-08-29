"""
Unknown Faces Management Page Module.

Requirements #22:
Displays unmatched face clusters, supports inspecting crops and source paths,
renaming unknown face groups, deleting face crops, and converting groups into new Profiles.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from services.unknown_face_service import UnknownFaceService


class UnknownFacesPage(QWidget):
    """Unknown Faces Page for inspecting and clustering unmatched faces."""

    def __init__(self, unknown_face_service: UnknownFaceService):
        super().__init__()
        self.unknown_face_service = unknown_face_service
        self.groups: list[dict[str, Any]] = []
        self.current_group_id: str | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        tb_layout = QHBoxLayout()
        sub_title = QLabel("Inspect unidentified faces. Auto-group similar faces and convert them into new person profiles with 1 click.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        tb_layout.addWidget(sub_title)

        btn_clear_all = QPushButton("🧹 Clear All")
        btn_clear_all.setProperty("class", "DangerButton")
        btn_clear_all.clicked.connect(self._clear_all_unknown_faces)
        tb_layout.addWidget(btn_clear_all)

        btn_cluster = QPushButton("✨ Auto-Group Similar Faces (80% Precision)")
        btn_cluster.setProperty("class", "PrimaryButton")
        btn_cluster.clicked.connect(self._run_clustering)
        tb_layout.addWidget(btn_cluster)

        layout.addLayout(tb_layout)

        # Main Splitter (Left: Groups List, Right: Group Faces Grid)
        splitter = QSplitter(Qt.Horizontal)

        left_w = QFrame()
        left_w.setProperty("class", "Card")
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(12, 12, 12, 12)
        left_l.setSpacing(8)

        left_lbl = QLabel("<b>Unknown Face Clusters:</b>")
        left_l.addWidget(left_lbl)

        self.groups_list = QListWidget()
        self.groups_list.itemSelectionChanged.connect(self._on_group_selected)
        left_l.addWidget(self.groups_list)

        splitter.addWidget(left_w)

        # Right Detail Area
        right_frame = QFrame()
        right_frame.setProperty("class", "Card")
        right_l = QVBoxLayout(right_frame)
        right_l.setSpacing(12)

        self.group_title_lbl = QLabel("Select an Unknown Face Group")
        self.group_title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        right_l.addWidget(self.group_title_lbl)

        # Actions
        actions_l = QHBoxLayout()

        self.btn_convert = QPushButton("⭐ Convert Group to New Profile")
        self.btn_convert.setProperty("class", "PrimaryButton")
        self.btn_convert.setFixedHeight(32)
        self.btn_convert.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: bold; padding: 0 16px;")
        self.btn_convert.clicked.connect(self._convert_group_to_profile)
        actions_l.addWidget(self.btn_convert)

        self.btn_add_to_existing = QPushButton("➕ Add to Existing Profile")
        self.btn_add_to_existing.setFixedHeight(32)
        self.btn_add_to_existing.setStyleSheet("background-color: #0284c7; color: #ffffff; font-weight: bold; border-radius: 8px; padding: 0 14px; border: 1px solid #0369a1;")
        self.btn_add_to_existing.clicked.connect(self._add_group_to_existing_profile)
        actions_l.addWidget(self.btn_add_to_existing)

        self.btn_rename_grp = QPushButton("✏️ Rename Group")
        self.btn_rename_grp.setProperty("class", "SecondaryButton")
        self.btn_rename_grp.setFixedHeight(32)
        self.btn_rename_grp.setStyleSheet("padding: 0 14px; font-weight: bold;")
        self.btn_rename_grp.clicked.connect(self._rename_group)
        actions_l.addWidget(self.btn_rename_grp)

        self.btn_delete_grp = QPushButton("🗑 Delete Group")
        self.btn_delete_grp.setProperty("class", "DangerButton")
        self.btn_delete_grp.setFixedHeight(32)
        self.btn_delete_grp.setStyleSheet("padding: 0 14px; font-weight: bold; background-color: #ef4444; color: #ffffff; border-radius: 8px;")
        self.btn_delete_grp.clicked.connect(self._delete_group)
        actions_l.addWidget(self.btn_delete_grp)

        actions_l.addStretch()
        right_l.addLayout(actions_l)

        # Faces scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll.setWidget(self.scroll_content)
        right_l.addWidget(self.scroll, 1)

        splitter.addWidget(right_frame)
        splitter.setSizes([260, 600])

        layout.addWidget(splitter, 1)

    def refresh(self):
        """Refresh unknown face groups list."""
        self._run_clustering()

    def _run_clustering(self):
        target_group_id = self.current_group_id
        self.groups = self.unknown_face_service.group_unknown_faces(threshold=50.0)
        self.groups_list.clear()

        select_row = -1
        for idx, g in enumerate(self.groups):
            g_id = g.get("group_id")
            g_name = g.get("group_name", "Unknown Group")
            faces_cnt = len(g.get("faces", []))
            item = QListWidgetItem(f"{g_name} ({faces_cnt} faces)")
            item.setData(Qt.UserRole, g_id)
            self.groups_list.addItem(item)
            if target_group_id and g_id == target_group_id:
                select_row = idx

        if self.groups_list.count() > 0:
            if select_row >= 0:
                self.groups_list.setCurrentRow(select_row)
            else:
                self.groups_list.setCurrentRow(0)

        if not self.groups:
            self.current_group_id = None
            self.group_title_lbl.setText("No unknown faces stored.")
            self._clear_faces_grid()

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
            self.group_title_lbl.setText(f"Group: {grp.get('group_name')}")
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

        card_width = 145
        spacing = 14
        viewport_w = self.scroll.viewport().width()
        available_w = max(400, viewport_w - 24)
        cols = max(2, available_w // (card_width + spacing))

        for idx, f in enumerate(faces):
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setStyleSheet(
                "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 8px;"
            )
            card.setFixedSize(140, 200)
            l = QVBoxLayout(card)
            l.setContentsMargins(6, 6, 6, 6)
            l.setSpacing(6)

            crop_path = f.get("crop_path")
            if crop_path and Path(crop_path).exists():
                pix = QPixmap(crop_path).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(pix)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setStyleSheet("border-radius: 6px; background-color: #1e293b;")
                l.addWidget(img_lbl)

            src_path_str = f.get("source_photo_path", "")
            src_file = Path(src_path_str).name if src_path_str else "Photo"
            src_lbl = QLabel(f"From: {src_file}")
            src_lbl.setWordWrap(True)
            src_lbl.setToolTip(src_path_str)
            src_lbl.setStyleSheet("font-size: 10px; color: #94a3b8;")
            l.addWidget(src_lbl)

            btn_del = QPushButton("🗑 Delete")
            btn_del.setProperty("class", "DangerButton")
            btn_del.setFixedHeight(24)
            btn_del.setStyleSheet("font-size: 11px; padding: 0 6px;")
            f_id = f.get("id")
            btn_del.clicked.connect(lambda _, u_id=f_id: self._delete_face(u_id))
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
            profile = self.unknown_face_service.convert_group_to_profile(self.current_group_id, name.strip())
            if profile:
                QMessageBox.information(self, "Success", f"Created Profile '{profile['name']}' from unknown face group.")
                self.refresh()

    def _add_group_to_existing_profile(self):
        if not self.current_group_id:
            return

        profiles = self.unknown_face_service.profile_service.list_profiles()
        if not profiles:
            QMessageBox.warning(self, "No Profiles Found", "No person profiles exist yet. Please create a profile first or use 'Convert Group to New Profile'.")
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

    def _delete_face(self, unknown_id: str):
        if unknown_id:
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
