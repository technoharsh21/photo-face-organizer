"""
Wrong Match Correction Dialog Component.

Requirement #28:
Allows non-technical users to reassign a photo that was incorrectly matched.
Removes the incorrect output copy from the person folder and safely copies it to 'No Match' or a chosen Profile.
Original source photo is NEVER modified.
"""

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class WrongMatchDialog(QDialog):
    """Dialog for correcting wrong photo matches."""

    def __init__(
        self,
        parent: QWidget | None,
        output_photo_path: Path,
        current_folder_name: str,
        available_profiles: list[dict[str, Any]],
    ):
        super().__init__(parent)
        self.setWindowTitle("Correct Photo Match")
        self.setMinimumWidth(450)
        self.output_photo_path = Path(output_photo_path)
        self.current_folder_name = current_folder_name
        self.available_profiles = available_profiles

        self.target_destination: str = "No Match"
        self.selected_profile_name: str | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel(f"✏️ Correct Photo Match: {self.output_photo_path.name}")
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        layout.addWidget(title)

        info = QLabel(
            f"Currently assigned to: <b>{self.current_folder_name}</b><br/>"
            "<span style='color: #10b981; font-size: 11px;'><b>Safety Guarantee:</b> Your original photo file will not be changed or deleted.</span>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        layout.addWidget(info)

        # Destination Selection
        self.radio_no_match = QRadioButton("Move to 'No Match' folder")
        self.radio_no_match.setChecked(True)
        self.radio_no_match.setStyleSheet("color: #ffffff;")

        self.radio_another = QRadioButton("Reassign to another Profile:")
        self.radio_another.setStyleSheet("color: #ffffff;")

        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_no_match, 0)
        self.btn_group.addButton(self.radio_another, 1)

        layout.addWidget(self.radio_no_match)
        layout.addWidget(self.radio_another)

        # Profile Combo
        self.profile_combo = QComboBox()
        for p in self.available_profiles:
            if p.get("name") != self.current_folder_name:
                self.profile_combo.addItem(p.get("name"), p.get("id"))
        self.profile_combo.setEnabled(False)
        layout.addWidget(self.profile_combo)

        self.radio_another.toggled.connect(self.profile_combo.setEnabled)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Apply Correction")
        confirm_btn.setProperty("class", "PrimaryButton")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        if self.radio_no_match.isChecked():
            self.target_destination = "No Match"
            self.selected_profile_name = None
            self.accept()
        else:
            txt = self.profile_combo.currentText().strip()
            if not txt:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "No Profile Selected", "Please select a target profile to reassign this photo to.")
                return
            self.target_destination = "Profile"
            self.selected_profile_name = txt
            self.accept()
