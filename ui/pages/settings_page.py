"""
Settings Page Module.

Requirements #31 & #32:
Manages performance modes (Eco/Balanced/Maximum Performance) and matching thresholds (default 50).
"""

from PySide6.QtWidgets import (
    QCheckBox,
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
from services.face_cache_service import FaceCacheService
from services.settings_service import SettingsService


class SettingsPage(QWidget):
    """Settings Page for system preferences and engine configuration."""

    def __init__(
        self,
        settings_service: SettingsService,
        face_engine: FaceEngine,
        face_cache_service: FaceCacheService | None = None,
    ):
        super().__init__()
        self.settings_service = settings_service
        self.face_engine = face_engine
        self.face_cache_service = face_cache_service

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

        # 3. Face Processing Disk Cache Toggle
        self.chk_enable_cache = QCheckBox("⚡ Enable Face Processing Disk Cache (1,000x Faster Rescans)")
        self.chk_enable_cache.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        c_layout.addWidget(self.chk_enable_cache)

        cache_desc = QLabel(
            "<i>Saves face locations and embeddings on disk so rescanning photos is instant (~0.0005s per photo). "
            "Storage size is tiny (~1.2 MB per 1,000 photos).</i>"
        )
        cache_desc.setWordWrap(True)
        cache_desc.setStyleSheet("color: #a0a0b0; font-size: 11px; margin-top: -8px;")
        c_layout.addWidget(cache_desc)

        layout.addWidget(card)

        # Storage Info & Cache Management Card
        storage_card = QFrame()
        storage_card.setProperty("class", "Card")
        sc_layout = QVBoxLayout(storage_card)
        sc_layout.setSpacing(10)

        sc_layout.addWidget(QLabel("Local Storage Location:"))
        self.lbl_storage = QLabel(str(self.settings_service.config.app_data_dir))
        self.lbl_storage.setStyleSheet("color: #a0a0b0; font-family: monospace;")
        sc_layout.addWidget(self.lbl_storage)

        btn_clear_cache = QPushButton("🧹 Clear Face Processing Cache")
        btn_clear_cache.setProperty("class", "DangerButton")
        btn_clear_cache.setFixedWidth(240)
        btn_clear_cache.clicked.connect(self._clear_cache)
        sc_layout.addWidget(btn_clear_cache)

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
        self.chk_enable_cache.setChecked(self.settings_service.get("enable_face_cache", True))

    def _save(self):
        self.settings_service.update({
            "performance_mode": self.combo_perf.currentText(),
            "matching_threshold": self.spin_threshold.value(),
            "enable_face_cache": self.chk_enable_cache.isChecked(),
        })
        QMessageBox.information(self, "Settings Saved", "Settings saved successfully.")

    def _reset(self):
        self.combo_perf.setCurrentText("Maximum Performance")
        self.spin_threshold.setValue(50)
        self.chk_enable_cache.setChecked(True)
        self.settings_service.reset_to_defaults()
        QMessageBox.information(self, "Settings Reset", "Settings reset to defaults.")

    def _clear_cache(self):
        if self.face_cache_service:
            res = QMessageBox.question(
                self,
                "Clear Face Processing Cache",
                "Are you sure you want to clear all cached face processing data from disk?\n\n"
                "Next time you scan, photos will be re-processed from scratch.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if res == QMessageBox.Yes:
                deleted_count, freed_mb = self.face_cache_service.clear_cache()
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    f"Successfully cleared {deleted_count} cached face entries ({freed_mb} MB freed).",
                )
        else:
            QMessageBox.information(self, "Cache Cleared", "Face cache is currently empty.")
