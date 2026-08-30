"""
Diagnostic Log Viewer Dialog Module.

Allows users to view recent system and AI hardware logs,
copy logs to clipboard, and open the log file in Explorer / Text Editor.
"""

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogViewerDialog(QDialog):
    """Modal dialog displaying recent application logs and diagnostic information."""

    def __init__(self, parent: QWidget | None, log_file_path: Path):
        super().__init__(parent)
        self.setWindowTitle("System & Hardware Diagnostic Logs")
        self.setMinimumSize(780, 520)
        self.log_file_path = Path(log_file_path)

        self._setup_ui()
        self._load_logs()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        hdr = QLabel("<b>Hardware Acceleration & Diagnostic Logs</b>")
        hdr.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(hdr)

        path_lbl = QLabel(f"Log File: {self.log_file_path}")
        path_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: monospace;")
        path_lbl.setWordWrap(True)
        layout.addWidget(path_lbl)

        # Text Area for Logs
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #38bdf8;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.txt_logs)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        btn_copy = QPushButton("📋 Copy Logs to Clipboard")
        btn_copy.setProperty("class", "SecondaryButton")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setFixedHeight(38)
        btn_copy.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_copy.clicked.connect(self._copy_logs)
        btn_box.addWidget(btn_copy)

        btn_open = QPushButton("📂 Open Log File")
        btn_open.setProperty("class", "SecondaryButton")
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setFixedHeight(38)
        btn_open.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_open.clicked.connect(self._open_log_file)
        btn_box.addWidget(btn_open)

        btn_box.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "PrimaryButton")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 24px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        layout.addLayout(btn_box)

    def _load_logs(self):
        if not self.log_file_path.exists():
            self.txt_logs.setText("No log file found yet. Logs will appear after scanning or initializing hardware.")
            return

        try:
            content = self.log_file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            # Show last 250 lines if very large
            if len(lines) > 250:
                lines = lines[-250:]
            self.txt_logs.setText("\n".join(lines))
            # Scroll to bottom
            sb = self.txt_logs.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception as e:
            self.txt_logs.setText(f"Error reading log file: {e}")

    def _copy_logs(self):
        text = self.txt_logs.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copied", "Diagnostic logs copied to clipboard!")

    def _open_log_file(self):
        if not self.log_file_path.exists():
            QMessageBox.warning(self, "File Not Found", "Log file does not exist yet.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(str(self.log_file_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.log_file_path)])
            else:
                subprocess.Popen(["xdg-open", str(self.log_file_path)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open log file: {e}")
