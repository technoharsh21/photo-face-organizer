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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Unknown (Unmatched) Faces")
        header.setProperty("class", "PageHeader")
        layout.addWidget(header)

        # Toolbar
        tb_layout = QHBoxLayout()

        btn_cluster = QPushButton("🔄 Group Similar Faces")
        btn_cluster.setProperty("class", "PrimaryButton")
        btn_cluster.setFixedHeight(34)
        btn_cluster.setStyleSheet("padding: 0 16px; font-weight: bold;")
        btn_cluster.clicked.connect(self._run_clustering)
        tb_layout.addWidget(btn_cluster)

        tb_layout.addStretch()
        layout.addLayout(tb_layout)

        # Main Splitter (Left: Groups List, Right: Group Faces Grid)
        splitter = QSplitter(Qt.Horizontal)

        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(8)

        left_lbl = QLabel("Unknown Person Groups")
        left_lbl.setStyleSheet("font-weight: bold; color: #a0a0b0; font-size: 13px;")
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

        self.btn_convert = QPushButton("⭐ Convert Group to Profile")
        self.btn_convert.setProperty("class", "PrimaryButton")
        self.btn_convert.setFixedHeight(32)
        self.btn_convert.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: bold; padding: 0 16px;")
        self.btn_convert.clicked.connect(self._convert_group_to_profile)
        actions_l.addWidget(self.btn_convert)

        self.btn_rename_grp = QPushButton("✏️ Rename Group")
        self.btn_rename_grp.setProperty("class", "SecondaryButton")
        self.btn_rename_grp.setFixedHeight(32)
        self.btn_rename_grp.setStyleSheet("padding: 0 14px; font-weight: bold;")
        self.btn_rename_grp.clicked.connect(self._rename_group)
        actions_l.addWidget(self.btn_rename_grp)

        actions_l.addStretch()
        right_l.addLayout(actions_l)

        # Faces scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QWidget()
        self.grid_layout = QHBoxLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(12)

        self.scroll.setWidget(self.scroll_content)
        right_l.addWidget(self.scroll)

        splitter.addWidget(right_frame)
        splitter.setSizes([260, 600])

        layout.addWidget(splitter)

    def refresh(self):
        """Refresh unknown face groups list."""
        self._run_clustering()

    def _run_clustering(self):
        self.groups = self.unknown_face_service.group_unknown_faces(threshold=50.0)
        self.groups_list.clear()

        for g in self.groups:
            g_name = g.get("group_name", "Unknown Group")
            faces_cnt = len(g.get("faces", []))
            item = QListWidgetItem(f"{g_name} ({faces_cnt} faces)")
            item.setData(Qt.UserRole, g.get("group_id"))
            self.groups_list.addItem(item)

        if not self.groups:
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

    def _display_faces(self, faces: list[dict[str, Any]]):
        self._clear_faces_grid()

        for f in faces:
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setStyleSheet(
                "background-color: #181820; border: 1px solid #2a2a3a; border-radius: 8px; padding: 10px;"
            )
            card.setFixedWidth(150)
            l = QVBoxLayout(card)
            l.setSpacing(8)

            crop_path = f.get("crop_path")
            if crop_path and Path(crop_path).exists():
                pix = QPixmap(crop_path).scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(pix)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setStyleSheet("border-radius: 6px;")
                l.addWidget(img_lbl)

            src_path_str = f.get("source_photo_path", "")
            src_file = Path(src_path_str).name if src_path_str else "Photo"
            src_lbl = QLabel(f"From: {src_file}")
            src_lbl.setWordWrap(True)
            src_lbl.setToolTip(src_path_str)
            src_lbl.setStyleSheet("font-size: 11px; color: #e0e0e0; font-weight: bold;")
            l.addWidget(src_lbl)

            btn_del = QPushButton("🗑 Delete")
            btn_del.setProperty("class", "DangerButton")
            btn_del.setFixedHeight(26)
            btn_del.setStyleSheet("font-size: 11px; padding: 0 8px;")
            f_id = f.get("id")
            btn_del.clicked.connect(lambda _, u_id=f_id: self._delete_face(u_id))
            l.addWidget(btn_del)

            self.grid_layout.addWidget(card)

        self.grid_layout.addStretch()

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

    def _delete_face(self, unknown_id: str):
        if unknown_id:
            self.unknown_face_service.delete_unknown_face(unknown_id)
            self.refresh()
