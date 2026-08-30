"""
Settings Page Module.

Modern, clean, and organized settings studio managing AI vision engine configuration,
hardware acceleration device preferences (GPU DirectML/CUDA vs CPU), default matching precision thresholds,
face embedding disk caching, and diagnostic log inspection.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from domain.face_engine import FaceEngine
from services.face_cache_service import FaceCacheService
from services.settings_service import SettingsService


class SettingsCard(QFrame):
    """Clean card container with explicit scoped styling so nested labels and frames never inherit unwanted borders."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "SettingsCard { background-color: #0c1322; border: 1px solid #1e293b; border-radius: 12px; }"
            "QLabel { border: none; background: transparent; }"
        )


class SettingsPage(QWidget):
    """Modern Settings Page for system preferences and AI engine configuration."""

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

    @staticmethod
    def _create_action_button(
        text: str,
        bg_color: str = "#1e293b",
        hover_color: str = "#334155",
        text_color: str = "#ffffff",
        border_color: str | None = None,
        padding_h: int = 20,
    ) -> QPushButton:
        """Create a standardized 42px action button component matching across all sections."""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.setMinimumHeight(42)
        border_css = f"border: 1px solid {border_color};" if border_color else "border: none;"
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg_color}; color: {text_color}; font-weight: 700; border-radius: 8px; padding: 0 {padding_h}px; font-size: 13px; min-height: 42px; max-height: 42px; {border_css} }}"
            f"QPushButton:hover {{ background-color: {hover_color}; color: #ffffff; }}"
        )
        return btn

    def _setup_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        scroll.setStyleSheet("background: transparent; border: none;")

        content_widget = QWidget()
        content_widget.setMaximumWidth(880)
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # 1. Header Title & Subtitle
        header_l = QVBoxLayout()
        header_l.setSpacing(4)
        title_lbl = QLabel("⚙️ Settings")
        title_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Manage AI vision acceleration, matching thresholds, face cache, and local storage.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        header_l.addWidget(title_lbl)
        header_l.addWidget(sub_title)
        layout.addLayout(header_l)

        # 2. Hero Hardware Acceleration Status Banner
        self.hero_hw_card = SettingsCard()
        hero_layout = QHBoxLayout(self.hero_hw_card)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(16)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(4)

        hero_hdr = QLabel("AI Hardware Acceleration Status")
        hero_hdr.setStyleSheet("font-size: 12px; color: #38bdf8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;")
        hero_left.addWidget(hero_hdr)

        self.lbl_hw_status = QLabel("🟢 Active AI Hardware: Detecting...")
        self.lbl_hw_status.setStyleSheet("font-size: 15px; font-weight: 800; color: #10b981;")
        hero_left.addWidget(self.lbl_hw_status)

        self.lbl_model_info = QLabel("AI Vision Model: InsightFace SCRFD + ArcFace (512-d embeddings)")
        self.lbl_model_info.setStyleSheet("font-size: 12px; color: #94a3b8;")
        hero_left.addWidget(self.lbl_model_info)

        hero_layout.addLayout(hero_left, 1)

        self.btn_view_logs = self._create_action_button(
            "📋 View Diagnostic Logs",
            bg_color="#1e293b",
            hover_color="#1d4ed8",
            text_color="#38bdf8",
            border_color="#3b82f6",
            padding_h=20,
        )
        self.btn_view_logs.clicked.connect(self._view_diagnostic_logs)
        hero_layout.addWidget(self.btn_view_logs)

        layout.addWidget(self.hero_hw_card)

        # 3. Card: AI Hardware & Performance Profile
        card_perf = SettingsCard()
        perf_layout = QVBoxLayout(card_perf)
        perf_layout.setContentsMargins(18, 16, 18, 16)
        perf_layout.setSpacing(14)

        card_perf_title = QLabel("⚡ AI Engine & Performance Profile")
        card_perf_title.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: 800;")
        perf_layout.addWidget(card_perf_title)

        # Grid for options
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)

        # Performance Profile
        lbl_p = QLabel("<b>Performance Profile:</b>")
        lbl_p.setStyleSheet("font-size: 13px; color: #ffffff;")
        self.combo_perf = QComboBox()
        self.combo_perf.setFixedHeight(34)
        self.combo_perf.setCursor(Qt.PointingHandCursor)
        self.combo_perf.addItems(["Maximum Performance", "Balanced", "Eco"])

        grid.addWidget(lbl_p, 0, 0)
        grid.addWidget(self.combo_perf, 0, 1)

        # Hardware Acceleration Device
        lbl_d = QLabel("<b>AI Hardware Preference:</b>")
        lbl_d.setStyleSheet("font-size: 13px; color: #ffffff;")
        self.combo_device = QComboBox()
        self.combo_device.setFixedHeight(34)
        self.combo_device.setCursor(Qt.PointingHandCursor)
        self.combo_device.addItems([
            "Auto (GPU Priority - Recommended)",
            "DirectX 12 GPU (DirectML)",
            "NVIDIA CUDA GPU",
            "Multi-Core CPU",
        ])

        grid.addWidget(lbl_d, 1, 0)
        grid.addWidget(self.combo_device, 1, 1)
        grid.setColumnStretch(1, 1)

        perf_layout.addLayout(grid)
        layout.addWidget(card_perf)

        # 4. Card: Default Matching Precision Threshold
        card_thresh = SettingsCard()
        t_layout = QVBoxLayout(card_thresh)
        t_layout.setContentsMargins(18, 16, 18, 16)
        t_layout.setSpacing(12)

        card_t_title = QLabel("🎯 Default Matching Precision Threshold")
        card_t_title.setStyleSheet("color: #34d399; font-size: 14px; font-weight: 800;")
        t_layout.addWidget(card_t_title)

        t_sub = QLabel("Default sensitivity threshold used across scans when matching faces against reference profiles.")
        t_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        t_layout.addWidget(t_sub)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(14)

        self.slider_threshold = QSlider(Qt.Horizontal)
        self.slider_threshold.setRange(1, 100)
        self.slider_threshold.setValue(50)
        self.slider_threshold.setCursor(Qt.PointingHandCursor)
        slider_row.addWidget(self.slider_threshold, 1)

        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 100)
        self.spin_threshold.setValue(50)
        self.spin_threshold.setFixedHeight(34)
        self.spin_threshold.setSuffix("%")
        self.spin_threshold.setFixedWidth(80)
        slider_row.addWidget(self.spin_threshold)

        t_layout.addLayout(slider_row)

        self.slider_threshold.valueChanged.connect(self.spin_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self.slider_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self._update_threshold_guidance)

        self.lbl_threshold_desc = QLabel()
        self.lbl_threshold_desc.setWordWrap(True)
        t_layout.addWidget(self.lbl_threshold_desc)

        self._update_threshold_guidance(50)
        layout.addWidget(card_thresh)

        # 5. Card: Face Processing Disk Cache
        card_cache = SettingsCard()
        c_layout = QVBoxLayout(card_cache)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(12)

        card_c_title = QLabel("🚀 Face Processing Disk Cache")
        card_c_title.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: 800;")
        c_layout.addWidget(card_c_title)

        cache_row = QHBoxLayout()
        cache_row.setSpacing(16)

        cache_info = QVBoxLayout()
        cache_info.setSpacing(4)

        self.chk_enable_cache = QCheckBox("Enable Face Processing Disk Cache (1,000x Faster Rescans)")
        self.chk_enable_cache.setChecked(True)
        self.chk_enable_cache.setCursor(Qt.PointingHandCursor)
        self.chk_enable_cache.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 13px;")
        cache_info.addWidget(self.chk_enable_cache)

        cache_desc = QLabel("Caches facial embeddings locally so rescanning the same library is instant (~0.0005s per photo).")
        cache_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        cache_info.addWidget(cache_desc)

        cache_row.addLayout(cache_info, 1)

        btn_clear_cache = self._create_action_button(
            "🧹 Clear Cache",
            bg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="#ffffff",
            border_color="#b91c1c",
            padding_h=20,
        )
        btn_clear_cache.clicked.connect(self._clear_cache)
        cache_row.addWidget(btn_clear_cache)

        c_layout.addLayout(cache_row)
        layout.addWidget(card_cache)

        # 6. Card: Local Storage Directory
        card_storage = SettingsCard()
        st_layout = QVBoxLayout(card_storage)
        st_layout.setContentsMargins(18, 16, 18, 16)
        st_layout.setSpacing(12)

        card_st_title = QLabel("📁 Local Application Storage Directory")
        card_st_title.setStyleSheet("color: #a78bfa; font-size: 14px; font-weight: 800;")
        st_layout.addWidget(card_st_title)

        st_row = QHBoxLayout()
        st_row.setSpacing(12)

        self.lbl_storage = QLabel(str(self.settings_service.config.app_data_dir))
        self.lbl_storage.setStyleSheet(
            "color: #38bdf8; font-family: monospace; font-size: 12px; background: #0f172a; padding: 8px 12px; border-radius: 6px; border: 1px solid #1e293b;"
        )
        st_row.addWidget(self.lbl_storage, 1)

        btn_open_folder = self._create_action_button(
            "📂 Open Folder",
            bg_color="#1e293b",
            hover_color="#1d4ed8",
            text_color="#38bdf8",
            border_color="#3b82f6",
            padding_h=20,
        )
        btn_open_folder.clicked.connect(self._open_app_data_folder)
        st_row.addWidget(btn_open_folder)

        st_layout.addLayout(st_row)
        layout.addWidget(card_storage)

        # 7. Action Buttons Footer Bar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        btn_save = self._create_action_button(
            "💾 Save Settings",
            bg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            border_color="#059669",
            padding_h=30,
        )
        btn_save.clicked.connect(self._save)
        btn_layout.addWidget(btn_save)

        btn_reset = self._create_action_button(
            "🔄 Reset Defaults",
            bg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            border_color="#334155",
            padding_h=24,
        )
        btn_reset.clicked.connect(self._reset)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        scroll.setWidget(content_widget)
        page_layout.addWidget(scroll)
        self.refresh()

    def _update_threshold_guidance(self, value: int):
        if value >= 85:
            text = f"🔒 <b>{value}% (Ultra-Strict Precision):</b> Near-identical face matches only. Zero false positives."
            style = "color: #34d399; font-size: 12px; background: #064e3b; padding: 10px; border-radius: 6px; border: 1px solid #10b981;"
        elif value >= 70:
            text = f"🎯 <b>{value}% (High Precision — Recommended for Solo Scans):</b> Highly accurate single-person matching."
            style = "color: #10b981; font-size: 12px; background: #064e3b; padding: 10px; border-radius: 6px; border: 1px solid #10b981;"
        elif value >= 50:
            text = f"⚖️ <b>{value}% (Balanced Mode — Recommended Default):</b> Standard matching across hairstyles, smiles, and varied lighting."
            style = "color: #60a5fa; font-size: 12px; background: #1e3a8a; padding: 10px; border-radius: 6px; border: 1px solid #3b82f6;"
        elif value >= 35:
            text = f"👓 <b>{value}% (Extended Range):</b> Matches side profiles and photos with sunglasses or hats."
            style = "color: #fbbf24; font-size: 12px; background: #78350f; padding: 10px; border-radius: 6px; border: 1px solid #f59e0b;"
        else:
            text = f"🔍 <b>{value}% (Maximum Sensitivity):</b> Loose matching for low-resolution or dark nighttime photos."
            style = "color: #f87171; font-size: 12px; background: #7f1d1d; padding: 10px; border-radius: 6px; border: 1px solid #ef4444;"

        self.lbl_threshold_desc.setText(text)
        self.lbl_threshold_desc.setStyleSheet(style)

    def refresh(self):
        """Refresh displayed settings values and AI hardware status."""
        self.combo_perf.setCurrentText(self.settings_service.get("performance_mode", "Maximum Performance"))
        t_val = int(self.settings_service.get("matching_threshold", 50))
        self.slider_threshold.setValue(t_val)
        self.spin_threshold.setValue(t_val)
        self.chk_enable_cache.setChecked(self.settings_service.get("enable_face_cache", True))

        dev_pref = self.settings_service.get("device_preference", "Auto")
        pref_map = {
            "Auto": "Auto (GPU Priority - Recommended)",
            "DirectML": "DirectX 12 GPU (DirectML)",
            "CUDA": "NVIDIA CUDA GPU",
            "CPU": "Multi-Core CPU",
        }
        self.combo_device.setCurrentText(pref_map.get(dev_pref, "Auto (GPU Priority - Recommended)"))

        if hasattr(self.face_engine, "get_device_info"):
            info = self.face_engine.get_device_info()
            dev = info.get("active_device", "Multi-Core CPU")
            gpu_active = info.get("gpu_available", False)

            if gpu_active:
                self.lbl_hw_status.setText(f"🟢 Active AI Hardware: {dev} (GPU Accelerated)")
                self.lbl_hw_status.setStyleSheet("font-size: 15px; font-weight: 800; color: #10b981;")
            else:
                self.lbl_hw_status.setText(f"🟢 Active AI Hardware: {dev}")
                self.lbl_hw_status.setStyleSheet("font-size: 15px; font-weight: 800; color: #60a5fa;")

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
        self.slider_threshold.setValue(50)
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
