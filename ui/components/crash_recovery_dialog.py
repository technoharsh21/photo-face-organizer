"""
Crash Recovery Dialog Component.

Requirement #26:
Displays prompt when an interrupted or crash-terminated scan is detected upon application startup.
Options:
- Resume: Continues from saved checkpoint.
- Restart: Restarts scan from 0.
- Discard Recovery: Removes checkpoint metadata without deleting photos.
"""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CrashRecoveryDialog(QDialog):
    """Startup modal for handling interrupted scan recovery."""

    def __init__(self, parent: QWidget | None, interrupted_scan_data: dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle("Interrupted Scan Detected")
        self.setMinimumWidth(480)
        self.scan_data = interrupted_scan_data
        self.chosen_action: str = "discard"  # 'resume', 'restart', 'discard'

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("⚠️ Previous Scan Interrupted")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f59e0b;")
        layout.addWidget(title)

        scan_id = self.scan_data.get("scan_id", "Unknown")
        cp = self.scan_data.get("checkpoint", {})
        processed = cp.get("processed_count", 0)
        total = cp.get("total_files", 0)
        start_time = self.scan_data.get("start_time", "Recent")

        info_text = (
            f"The scan started on <b>{start_time}</b> was interrupted.<br>"
            f"Progress saved: <b>{processed} of {total} photos processed</b>.<br><br>"
            "Would you like to resume processing from where it left off, restart from the beginning, or discard recovery?"
        )
        msg_label = QLabel(info_text)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        layout.addWidget(msg_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        discard_btn = QPushButton("Discard Recovery")
        discard_btn.setProperty("class", "DangerButton")
        discard_btn.setCursor(Qt.PointingHandCursor)
        discard_btn.setFixedHeight(36)
        discard_btn.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        discard_btn.clicked.connect(self._on_discard)
        btn_layout.addWidget(discard_btn)

        btn_layout.addStretch()

        restart_btn = QPushButton("Restart")
        restart_btn.setProperty("class", "SecondaryButton")
        restart_btn.setCursor(Qt.PointingHandCursor)
        restart_btn.setFixedHeight(36)
        restart_btn.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        restart_btn.clicked.connect(self._on_restart)
        btn_layout.addWidget(restart_btn)

        resume_btn = QPushButton("Resume Scan")
        resume_btn.setProperty("class", "PrimaryButton")
        resume_btn.setCursor(Qt.PointingHandCursor)
        resume_btn.setFixedHeight(36)
        resume_btn.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        resume_btn.clicked.connect(self._on_resume)
        btn_layout.addWidget(resume_btn)

        layout.addLayout(btn_layout)

    def _on_resume(self):
        self.chosen_action = "resume"
        self.accept()

    def _on_restart(self):
        self.chosen_action = "restart"
        self.accept()

    def _on_discard(self):
        self.chosen_action = "discard"
        self.accept()
