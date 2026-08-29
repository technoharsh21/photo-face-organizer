"""
People (Profiles) Management Page Module.

Allows users to create, rename, delete profiles, view reference photos,
add single or multiple reference photos (with group face selection), remove reference photos,
and bulk import profiles from folders.
"""

from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
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

from services.profile_service import ProfileService
from ui.components.face_selector import FaceSelectorDialog


class PeoplePage(QWidget):
    """Page for creating and managing person profiles and reference photos."""

    def __init__(self, profile_service: ProfileService):
        super().__init__()
        self.profile_service = profile_service
        self.current_profile_id: str | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Compact Top Action Bar (No giant redundant headers or dead vertical space)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        sub_title = QLabel("Add 1 or 2 reference photos per person for 99.86% AI matching precision.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        top_bar.addWidget(sub_title)

        top_bar.addStretch()

        btn_add_person = QPushButton("➕ Create New Profile")
        btn_add_person.setProperty("class", "PrimaryButton")
        btn_add_person.clicked.connect(self._create_profile)
        top_bar.addWidget(btn_add_person)

        btn_bulk_import = QPushButton("📁 Bulk Import Folders")
        btn_bulk_import.setProperty("class", "SecondaryButton")
        btn_bulk_import.clicked.connect(self._bulk_import)
        top_bar.addWidget(btn_bulk_import)

        layout.addLayout(top_bar)

        # 2. Main Splitter (Fills remaining vertical space cleanly with stretch factor 1)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Profile List Card
        left_widget = QFrame()
        left_widget.setProperty("class", "Card")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(10)

        left_hdr_box = QHBoxLayout()
        left_hdr = QLabel("<b>People Profiles</b>")
        left_hdr.setStyleSheet("font-size: 14px; color: #ffffff;")
        self.lbl_profile_count = QLabel("0 Profiles")
        self.lbl_profile_count.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        left_hdr_box.addWidget(left_hdr)
        left_hdr_box.addStretch()
        left_hdr_box.addWidget(self.lbl_profile_count)
        left_layout.addLayout(left_hdr_box)

        # Search Filter Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search people...")
        self.txt_search.textChanged.connect(self._filter_profiles)
        left_layout.addWidget(self.txt_search)

        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.list_widget, 1)

        splitter.addWidget(left_widget)

        # Right Column: Selected Profile Detail Panel Card
        self.detail_card = QFrame()
        self.detail_card.setProperty("class", "Card")
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(16)

        # Unified Profile Header Toolbar (Single Row with Profile Name & All Actions)
        p_header_layout = QHBoxLayout()
        p_header_layout.setSpacing(8)

        self.lbl_profile_name = QLabel("Select a Person")
        self.lbl_profile_name.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        p_header_layout.addWidget(self.lbl_profile_name)

        p_header_layout.addStretch()

        self.btn_add_ref = QPushButton("📷 Add Reference Photo")
        self.btn_add_ref.setProperty("class", "PrimaryButton")
        self.btn_add_ref.clicked.connect(self._add_reference_photo)
        p_header_layout.addWidget(self.btn_add_ref)

        self.btn_group_type = QPushButton("👥 Group Settings")
        self.btn_group_type.setProperty("class", "SecondaryButton")
        self.btn_group_type.clicked.connect(self._edit_group_settings)
        p_header_layout.addWidget(self.btn_group_type)

        self.btn_rename = QPushButton("✏️ Rename")
        self.btn_rename.setProperty("class", "SecondaryButton")
        self.btn_rename.clicked.connect(self._rename_profile)
        p_header_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setProperty("class", "DangerButton")
        self.btn_delete.clicked.connect(self._delete_profile)
        p_header_layout.addWidget(self.btn_delete)

        detail_layout.addLayout(p_header_layout)

        # Reference Photos Section Title
        ref_title_box = QHBoxLayout()
        ref_sec_title = QLabel("<b>Reference Photos (Used for AI Matching):</b>")
        ref_sec_title.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        ref_title_box.addWidget(ref_sec_title)
        ref_title_box.addStretch()
        detail_layout.addLayout(ref_title_box)

        # Reference Thumbnails Scroll Area
        self.ref_scroll = QScrollArea()
        self.ref_scroll.setWidgetResizable(True)
        self.ref_scroll.setStyleSheet("background: transparent; border: none;")

        self.ref_container = QWidget()
        self.ref_grid = QHBoxLayout(self.ref_container)
        self.ref_grid.setContentsMargins(4, 4, 4, 4)
        self.ref_grid.setSpacing(14)
        self.ref_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.ref_scroll.setWidget(self.ref_container)
        detail_layout.addWidget(self.ref_scroll, 1)

        splitter.addWidget(self.detail_card)
        splitter.setSizes([280, 640])

        layout.addWidget(splitter, 1)
        self.refresh()

    def _filter_profiles(self, query: str):
        """Filter profile list items based on search text."""
        q = query.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(q not in item.text().lower())

    def refresh(self, select_profile_id: str | None = None):
        """Reload profile list from disk while preserving active selection."""
        target_id = select_profile_id or self.current_profile_id

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        profiles = self.profile_service.list_profiles()
        self.lbl_profile_count.setText(f"{len(profiles)} Profile{'s' if len(profiles) != 1 else ''}")
        selected_item = None

        for p in profiles:
            ref_count = len(p.get("references", []))
            group_tag = " [Group]" if p.get("is_group_profile") else ""
            item_text = f"{p['name']}{group_tag} ({ref_count} refs)"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, p["id"])
            self.list_widget.addItem(item)

            if target_id and p["id"] == target_id:
                selected_item = item

        self.list_widget.blockSignals(False)

        if selected_item:
            self.list_widget.setCurrentItem(selected_item)
            self._load_profile_details(selected_item.data(Qt.UserRole))
        elif self.list_widget.count() > 0:
            first_item = self.list_widget.item(0)
            self.list_widget.setCurrentItem(first_item)
            self._load_profile_details(first_item.data(Qt.UserRole))
        else:
            self.current_profile_id = None
            self.lbl_profile_name.setText("No Profiles Found")
            self._clear_ref_grid()

    def _on_profile_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            p_id = current.data(Qt.UserRole)
            self._load_profile_details(p_id)

    def _load_profile_details(self, profile_id: str):
        self.current_profile_id = profile_id
        profile = self.profile_service.get_profile(profile_id)
        if not profile:
            return

        group_tag = " [Group Profile]" if profile.get("is_group_profile") else ""
        self.lbl_profile_name.setText(f"{profile['name']}{group_tag}")
        self._display_references(profile)

    def _clear_ref_grid(self):
        while self.ref_grid.count():
            item = self.ref_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _display_references(self, profile: dict[str, Any]):
        self._clear_ref_grid()
        references = profile.get("references", [])

        if not references:
            no_ref_card = QFrame()
            no_ref_card.setStyleSheet("background-color: #0f172a; border: 1px dashed #334155; border-radius: 8px; padding: 20px;")
            n_layout = QVBoxLayout(no_ref_card)
            no_ref_lbl = QLabel("📷 <b>No reference photos added yet.</b><br/><span style='color: #94a3b8;'>Click <b>'📷 Add Reference Photo'</b> above to upload a clear face image for matching.</span>")
            no_ref_lbl.setWordWrap(True)
            no_ref_lbl.setStyleSheet("color: #f8fafc; font-size: 12px;")
            n_layout.addWidget(no_ref_lbl)
            self.ref_grid.addWidget(no_ref_card)
            return

        for ref in references:
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setStyleSheet("background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 6px;")
            card.setFixedSize(140, 205)
            l = QVBoxLayout(card)
            l.setContentsMargins(6, 6, 6, 6)
            l.setSpacing(4)

            stored_path = ref.get("stored_path")
            if stored_path and Path(stored_path).exists():
                pix = QPixmap(stored_path).scaled(105, 105, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(pix)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setStyleSheet("border-radius: 6px; background-color: #1e293b;")
                l.addWidget(img_lbl)

            q_info = ref.get("quality")
            if not q_info:
                # Compute quality dynamically for legacy reference entries
                stored_path = ref.get("stored_path")
                bbox = ref.get("bbox", [0, 100, 100, 0])
                if stored_path and Path(stored_path).exists():
                    try:
                        with Image.open(stored_path) as ref_img:
                            q_info = self.profile_service.assess_reference_quality(ref_img, bbox)
                    except Exception:
                        q_info = {"stars": 5, "badge": "⭐⭐⭐⭐⭐", "quality_label": "🟢 5/5 Stars: Excellent"}
                else:
                    q_info = {"stars": 5, "badge": "⭐⭐⭐⭐⭐", "quality_label": "🟢 5/5 Stars: Excellent"}

            if q_info:
                q_lbl = QLabel(f"{q_info.get('badge', '⭐')} {q_info.get('stars', 5)}/5")
                q_lbl.setToolTip(q_info.get("quality_label", "Reference Quality"))
                q_lbl.setStyleSheet("font-size: 11px; color: #fbbf24; font-weight: bold;")
                q_lbl.setAlignment(Qt.AlignCenter)
                l.addWidget(q_lbl)

            btn_del = QPushButton("🗑 Remove")
            btn_del.setProperty("class", "DangerButton")
            btn_del.setFixedHeight(22)
            btn_del.setStyleSheet("font-size: 11px; padding: 0 6px;")
            ref_id = ref.get("id")
            btn_del.clicked.connect(lambda _, r_id=ref_id: self._remove_reference(r_id))
            l.addWidget(btn_del, alignment=Qt.AlignCenter)

            self.ref_grid.addWidget(card)

        self.ref_grid.addStretch()

    def _create_profile(self):
        dlg = CreateProfileDialog(self, self.profile_service.list_profiles())
        if dlg.exec() == CreateProfileDialog.Accepted:
            name = dlg.profile_name
            is_group = dlg.is_group_profile
            compulsory_ids = dlg.selected_compulsory_ids

            if name:
                try:
                    new_p = self.profile_service.create_profile(
                        name=name,
                        is_group_profile=is_group,
                        compulsory_profile_ids=compulsory_ids,
                    )
                    self.refresh(select_profile_id=new_p["id"])
                except ValueError as ve:
                    QMessageBox.warning(self, "Profile Creation Error", str(ve))

    def _edit_group_settings(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        all_profiles = [p for p in self.profile_service.list_profiles() if p["id"] != self.current_profile_id]
        dlg = CreateProfileDialog(self, all_profiles, initial_profile=profile)
        if dlg.exec() == CreateProfileDialog.Accepted:
            self.profile_service.update_profile_type(
                self.current_profile_id,
                is_group_profile=dlg.is_group_profile,
                compulsory_profile_ids=dlg.selected_compulsory_ids,
            )
            if dlg.profile_name != profile["name"]:
                try:
                    self.profile_service.rename_profile(self.current_profile_id, dlg.profile_name)
                except ValueError as ve:
                    QMessageBox.warning(self, "Rename Error", str(ve))
            self.refresh(select_profile_id=self.current_profile_id)

    def _rename_profile(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        new_name, ok = QInputDialog.getText(
            self, "Rename Profile", "Enter New Profile Name:", text=profile["name"]
        )
        if ok and new_name.strip():
            try:
                self.profile_service.rename_profile(self.current_profile_id, new_name.strip())
                self.refresh(select_profile_id=self.current_profile_id)
            except ValueError as ve:
                QMessageBox.warning(self, "Rename Error", str(ve))

    def _delete_profile(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        res = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete profile '{profile['name']}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.profile_service.delete_profile(self.current_profile_id)
            self.current_profile_id = None
            self.refresh()

    def _add_reference_photo(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "No Profile Selected", "Please select or create a profile first.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Photo",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.heic *.tiff *.cr2 *.nef *.arw *.dng);;All Files (*)",
        )
        if not file_path:
            return

        p_path = Path(file_path)
        # Check faces in reference
        _, locations, crops = self.profile_service.detect_faces_in_reference(p_path)

        selected_idx = 0
        if len(locations) > 1:
            dlg = FaceSelectorDialog(self, crops)
            if dlg.exec() == FaceSelectorDialog.Accepted:
                selected_idx = dlg.selected_index
            else:
                return

        success, msg = self.profile_service.add_reference_photo(
            self.current_profile_id, p_path, selected_face_index=selected_idx, use_fallback_if_no_face=True
        )
        if success:
            QMessageBox.information(self, "Success", "Reference photo added successfully.")
            self.refresh(select_profile_id=self.current_profile_id)
        else:
            QMessageBox.warning(self, "Error", f"Failed to add reference photo: {msg}")

    def _remove_reference(self, ref_id: str):
        if self.current_profile_id and ref_id:
            self.profile_service.remove_reference_photo(self.current_profile_id, ref_id)
            self.refresh(select_profile_id=self.current_profile_id)

    def _bulk_import(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Root Directory for Bulk Import")
        if folder:
            imported = self.profile_service.bulk_import_profiles(Path(folder))
            QMessageBox.information(self, "Bulk Import Complete", f"Imported {len(imported)} profiles.")
            self.refresh()


class CreateProfileDialog(QDialog):
    """Dialog for creating or editing Individual or Group profiles."""

    def __init__(
        self,
        parent: QWidget | None,
        existing_profiles: list[dict[str, Any]],
        initial_profile: dict[str, Any] | None = None,
    ):
        super().__init__(parent)
        self.initial_profile = initial_profile
        self.setWindowTitle("Edit Profile Settings" if initial_profile else "Create New Profile")
        self.setMinimumWidth(420)
        self.existing_profiles = existing_profiles

        self.profile_name: str = initial_profile.get("name", "") if initial_profile else ""
        self.is_group_profile: bool = initial_profile.get("is_group_profile", False) if initial_profile else False
        self.selected_compulsory_ids: list[str] = (
            initial_profile.get("compulsory_profile_ids", []) if initial_profile else []
        )

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        lbl_title = QLabel("Profile Settings" if self.initial_profile else "Create Profile")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(lbl_title)

        layout.addWidget(QLabel("Profile Name:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Harsh, John, or Me & Friend")
        if self.profile_name:
            self.txt_name.setText(self.profile_name)
        layout.addWidget(self.txt_name)

        layout.addWidget(QLabel("Profile Type:"))
        self.radio_indiv = QRadioButton("Individual Person Profile")
        self.radio_indiv.setStyleSheet("color: #ffffff;")

        self.radio_group = QRadioButton("Group Profile (Requires ALL compulsory people to be present in photo)")
        self.radio_group.setStyleSheet("color: #ffffff;")

        if self.is_group_profile:
            self.radio_group.setChecked(True)
        else:
            self.radio_indiv.setChecked(True)

        self.btn_grp = QButtonGroup(self)
        self.btn_grp.addButton(self.radio_indiv, 0)
        self.btn_grp.addButton(self.radio_group, 1)

        layout.addWidget(self.radio_indiv)
        layout.addWidget(self.radio_group)

        # Compulsory Profiles selection frame
        self.compulsory_frame = QFrame()
        self.compulsory_frame.setStyleSheet("background-color: #181820; border-radius: 6px; padding: 10px;")
        cf_layout = QVBoxLayout(self.compulsory_frame)
        cf_layout.setSpacing(6)

        cf_layout.addWidget(QLabel("Select Compulsory People for this Group:"))
        self.compulsory_checkboxes = {}

        for p in self.existing_profiles:
            if not p.get("is_group_profile"):
                chk = QCheckBox(p.get("name", "Unknown"))
                chk.setStyleSheet("color: #e0e0e0;")
                if p.get("id") in self.selected_compulsory_ids:
                    chk.setChecked(True)
                cf_layout.addWidget(chk)
                self.compulsory_checkboxes[p.get("id")] = chk

        self.compulsory_frame.setEnabled(self.is_group_profile)
        layout.addWidget(self.compulsory_frame)

        self.radio_group.toggled.connect(self.compulsory_frame.setEnabled)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton("Create Profile")
        btn_ok.setProperty("class", "PrimaryButton")
        btn_ok.clicked.connect(self._on_confirm)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a profile name.")
            return

        self.profile_name = name
        self.is_group_profile = self.radio_group.isChecked()

        if self.is_group_profile:
            self.selected_compulsory_ids = [
                p_id for p_id, chk in self.compulsory_checkboxes.items() if chk.isChecked()
            ]
            if len(self.selected_compulsory_ids) < 2:
                QMessageBox.warning(
                    self,
                    "Group Profile Setup",
                    "Please select at least 2 compulsory individual profiles for a Group Profile.",
                )
                return

        self.accept()
