"""
Settings Page Module.

Requirements #31 & #32:
Manages performance modes (Eco/Balanced/Maximum Performance) and matching thresholds (default 50).
"""

from PySide6.QtCore import Qt
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

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

        # 2. AI Hardware Device Preference
        c_layout.addWidget(QLabel("AI Hardware Acceleration Preference:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems([
            "Auto (GPU Priority - Recommended)",
            "DirectX 12 GPU (DirectML)",
            "NVIDIA CUDA GPU",
            "Multi-Core CPU"
        ])
        c_layout.addWidget(self.combo_device)

        # 3. Matching Threshold
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

        # AI Hardware Acceleration Status Card
        hw_card = QFrame()
        hw_card.setProperty("class", "Card")
        hw_card.setStyleSheet("background-color: #121824; border: 1px solid #1e3a8a; border-radius: 8px; padding: 14px;")
        hw_layout = QVBoxLayout(hw_card)
        hw_layout.setSpacing(6)

        hw_layout.addWidget(QLabel("<b>AI Hardware Acceleration Status:</b>"))
        self.lbl_hw_status = QLabel()
        self.lbl_hw_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #10b981;")
        hw_layout.addWidget(self.lbl_hw_status)

        self.lbl_model_info = QLabel()
        self.lbl_model_info.setStyleSheet("font-size: 11px; color: #a0a0b0;")
        hw_layout.addWidget(self.lbl_model_info)

        hw_btn_row = QHBoxLayout()
        self.btn_view_logs = QPushButton("📋 View Hardware & Diagnostic Logs")
        self.btn_view_logs.setProperty("class", "SecondaryButton")
        self.btn_view_logs.setCursor(Qt.PointingHandCursor)
        self.btn_view_logs.setFixedWidth(280)
        self.btn_view_logs.clicked.connect(self._view_diagnostic_logs)
        hw_btn_row.addWidget(self.btn_view_logs)
        hw_btn_row.addStretch()
        hw_layout.addLayout(hw_btn_row)

        layout.addWidget(hw_card)

        # Storage Info & Cache Management Card
        storage_card = QFrame()
        storage_card.setProperty("class", "Card")
        sc_layout = QVBoxLayout(storage_card)
        sc_layout.setSpacing(10)

        sc_layout.addWidget(QLabel("Local Storage Location:"))
        self.lbl_storage = QLabel(str(self.settings_service.config.app_data_dir))
        self.lbl_storage.setStyleSheet("color: #a0a0b0; font-family: monospace;")
        sc_layout.addWidget(self.lbl_storage)

        st_btn_row = QHBoxLayout()
        btn_open_folder = QPushButton("📂 Open App Data Folder")
        btn_open_folder.setProperty("class", "SecondaryButton")
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.setFixedWidth(200)
        btn_open_folder.clicked.connect(self._open_app_data_folder)
        st_btn_row.addWidget(btn_open_folder)

        btn_clear_cache = QPushButton("🧹 Clear Face Processing Cache")
        btn_clear_cache.setProperty("class", "DangerButton")
        btn_clear_cache.setCursor(Qt.PointingHandCursor)
        btn_clear_cache.setFixedWidth(240)
        btn_clear_cache.clicked.connect(self._clear_cache)
        st_btn_row.addWidget(btn_clear_cache)
        st_btn_row.addStretch()
        sc_layout.addLayout(st_btn_row)

        layout.addWidget(storage_card)

        # Action Buttons
        btn_layout = QHBoxLayout()

        btn_save = QPushButton("💾 Save Settings")
        btn_save.setProperty("class", "PrimaryButton")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setProperty("class", "SecondaryButton")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self._reset)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.refresh()

    def refresh(self):
        """Refresh displayed settings values and AI hardware status."""
        self.combo_perf.setCurrentText(self.settings_service.get("performance_mode", "Maximum Performance"))
        self.spin_threshold.setValue(int(self.settings_service.get("matching_threshold", 50)))
        self.chk_enable_cache.setChecked(self.settings_service.get("enable_face_cache", True))

        dev_pref = self.settings_service.get("device_preference", "Auto")
        pref_map = {
            "Auto": "Auto (GPU Priority - Recommended)",
            "DirectML": "DirectX 12 GPU (DirectML)",
            "CUDA": "NVIDIA CUDA GPU",
            "CPU": "Multi-Core CPU"
        }
        self.combo_device.setCurrentText(pref_map.get(dev_pref, "Auto (GPU Priority - Recommended)"))

        if hasattr(self.face_engine, "get_device_info"):
            info = self.face_engine.get_device_info()
            dev = info.get("active_device", "Multi-Core CPU")
            gpu_active = info.get("gpu_available", False)

            if gpu_active:
                self.lbl_hw_status.setText(f"🟢 Active AI Hardware: {dev} (GPU Accelerated)")
                self.lbl_hw_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #10b981;")
            else:
                self.lbl_hw_status.setText(f"🟢 Active AI Hardware: {dev}")
                self.lbl_hw_status.setStyleSheet("font-size: 13px; font-weight: bold; color: #60a5fa;")

            self.lbl_model_info.setText(f"AI Vision Model: {info.get('model_used', 'InsightFace SCRFD + ArcFace 512-d')}")

    def _save(self):
        sel_text = self.combo_device.currentText()
        pref = "Auto"
        if "DirectX" in sel_text or "DirectML" in sel_text:
            pref = "DirectML"
        elif "CUDA" in sel_text:
            pref = "CUDA"
        elif "CPU" in sel_text:
            pref = "CPU"

        self.settings_service.update({
            "performance_mode": self.combo_perf.currentText(),
            "device_preference": pref,
            "matching_threshold": self.spin_threshold.value(),
            "enable_face_cache": self.chk_enable_cache.isChecked(),
        })

        if hasattr(self.face_engine, "set_device_preference"):
            self.face_engine.set_device_preference(pref)

        self.refresh()
        QMessageBox.information(self, "Settings Saved", "Settings saved successfully.")

    def _reset(self):
        self.combo_perf.setCurrentText("Maximum Performance")
        self.combo_device.setCurrentText("Auto (GPU Priority - Recommended)")
        self.spin_threshold.setValue(50)
        self.chk_enable_cache.setChecked(True)
        self.settings_service.reset_to_defaults()
        if hasattr(self.face_engine, "set_device_preference"):
            self.face_engine.set_device_preference("Auto")
        self.refresh()
        QMessageBox.information(self, "Settings Reset", "Settings reset to defaults.")

    def _view_diagnostic_logs(self):
        from ui.components.log_viewer_dialog import LogViewerDialog
        log_file = self.settings_service.config.app_data_dir / "photo_face_organizer.log"
        dlg = LogViewerDialog(self, log_file)
        dlg.exec()

    def _open_app_data_folder(self):
        import os, subprocess, sys
        folder = str(self.settings_service.config.app_data_dir)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open folder: {e}")

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
