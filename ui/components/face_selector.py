"""
Face Selector Dialog Component.

Requirement #9: Group Reference Photos.
When a reference photo containing multiple faces is uploaded, this dialog shows
preview crops of all detected faces so the user can explicitly select the correct person's face.
The application must NEVER randomly select a face.
"""


from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class FaceSelectorDialog(QDialog):
    """Dialog for choosing the correct face from a multi-face reference photo."""

    def __init__(self, parent: QWidget | None, face_crops: list[Image.Image]):
        super().__init__(parent)
        self.setWindowTitle("Select Person's Face")
        self.setMinimumSize(500, 400)
        self.face_crops = face_crops
        self.selected_index: int | None = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header = QLabel("👤 Select the Correct Person's Face")
        header.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        layout.addWidget(header)

        instruction = QLabel(f"<b>Detected {len(self.face_crops)} faces</b> in this reference photo. Click to select the face that belongs to this person:")
        instruction.setWordWrap(True)
        instruction.setStyleSheet("color: #38bdf8; font-size: 12px;")
        layout.addWidget(instruction)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        grid_layout = QHBoxLayout(scroll_content)
        grid_layout.setSpacing(16)

        self.button_group = QButtonGroup(self)

        for i, crop in enumerate(self.face_crops):
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setStyleSheet("background-color: #25252e; border-radius: 8px; padding: 8px;")
            card_layout = QVBoxLayout(card)

            # Convert PIL image to QPixmap
            crop_rgb = crop.convert("RGB")
            data = crop_rgb.tobytes("raw", "RGB")
            qimg = QImage(data, crop_rgb.width, crop_rgb.height, crop_rgb.width * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(img_label)

            radio = QRadioButton(f"Face #{i + 1}")
            radio.setStyleSheet("color: #ffffff; font-weight: bold;")
            if i == 0:
                radio.setChecked(True)
            self.button_group.addButton(radio, i)
            card_layout.addWidget(radio, alignment=Qt.AlignCenter)

            grid_layout.addWidget(card)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("class", "SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("Use Selected Face")
        confirm_btn.setProperty("class", "PrimaryButton")
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        self.selected_index = self.button_group.checkedId()
        self.accept()
