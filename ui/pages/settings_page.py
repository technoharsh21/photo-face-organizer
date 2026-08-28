"""
Settings Page Module.

Requirements #31 & #32:
Manages performance modes (Eco/Balanced/Maximum Performance) and matching thresholds (default 50).
"""

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from domain.face_engine import FaceEngine
from services.settings_service import SettingsService


class SettingsPage(QWidget):
    """Settings Page for system preferences and engine configuration."""

    def __init__(self, settings_service: SettingsService, face_engine: FaceEngine):
        super().__init__()
        self.settings_service = settings_service
        self.face_engine = face_engine

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        header = QLabel("Application Settings")
        header.setProperty("class", "PageHeader")
        layout.addWidget(header)

        # Settings Card
        card = QFrame()
        card.setProperty("class", "Card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(16)

        # 1. Performance Mode
        c_layout.addWidget(QLabel("Performance Mode:"))
        self.combo_perf = QComboBox()
        self.combo_perf.addItems(["Eco", "Balanced", "Maximum Performance"])
        c_layout.addWidget(self.combo_perf)

        # 2. Matching Threshold
        c_layout.addWidget(QLabel("Default Matching Threshold (0 - 100, Default: 50):"))
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 100)
        c_layout.addWidget(self.spin_threshold)

        layout.addWidget(card)

        # Storage Info Card
        storage_card = QFrame()
        storage_card.setProperty("class", "Card")
        sc_layout = QVBoxLayout(storage_card)

        sc_layout.addWidget(QLabel("Local Storage Location:"))
        self.lbl_storage = QLabel(str(self.settings_service.config.app_data_dir))
        self.lbl_storage.setStyleSheet("color: #a0a0b0; font-family: monospace;")
        sc_layout.addWidget(self.lbl_storage)

        layout.addWidget(storage_card)

        # Action Buttons
        btn_layout = QHBoxLayout()

        btn_save = QPushButton("💾 Save Settings")
        btn_save.setProperty("class", "PrimaryButton")
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setProperty("class", "SecondaryButton")
        btn_reset.clicked.connect(self._reset)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.refresh()

    def refresh(self):
        """Refresh displayed settings values."""
        self.combo_perf.setCurrentText(self.settings_service.get("performance_mode", "Maximum Performance"))
        self.spin_threshold.setValue(int(self.settings_service.get("matching_threshold", 50)))

    def _save(self):
        self.settings_service.update({
            "performance_mode": self.combo_perf.currentText(),
            "matching_threshold": float(self.spin_threshold.value()),
        })

        self.refresh()
        QMessageBox.information(self, "Settings Saved", "Settings updated successfully.")

    def _reset(self):
        self.settings_service.reset_to_defaults()
        self.refresh()
        QMessageBox.information(self, "Settings Reset", "Settings reset to defaults.")
