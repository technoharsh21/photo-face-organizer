"""
Skipped Files & Error Details Dialog Module.

Displays an interactive audit table listing skipped and error files during a scan,
explaining exact reasons (e.g. Duplicate Skipped, Corrupted Image, Missing Source File),
and allowing 1-click Export of the complete Audit Log (.txt / .json) to disk.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SkippedFilesDialog(QDialog):
    """Modal dialog for reviewing skipped/error files with export capabilities."""

    def __init__(self, parent: QWidget | None, summary_data: dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle("Skipped & Error File Details")
        self.setMinimumSize(780, 520)
        self.summary_data = summary_data

        # Extract items
        self.items: list[dict[str, str]] = self._parse_items(summary_data)

        self._setup_ui()

    def _parse_items(self, data: dict[str, Any]) -> list[dict[str, str]]:
        items = []

        # 1. Parse errors_log
        errors_log = data.get("errors_log", [])
        for err_entry in errors_log:
            if isinstance(err_entry, dict):
                f_path = err_entry.get("file") or err_entry.get("file_path", "Unknown File")
                reason = err_entry.get("error", "Unreadable or corrupted image")
                items.append({
                    "path": str(f_path),
                    "status": "⚠️ Error / Corrupted",
                    "reason": reason,
                    "color": "#ef4444"
                })

        # 2. Parse source_to_output_map for DUPLICATE_SKIPPED entries
        src_map = data.get("source_to_output_map", {})
        for src_path, status_list in src_map.items():
            if isinstance(status_list, list):
                for st in status_list:
                    if "DUPLICATE_SKIPPED" in str(st):
                        items.append({
                            "path": str(src_path),
                            "status": "📁 Duplicate Skipped",
                            "reason": "Photo already exists in destination output folder (Skipped to prevent duplicate file copies)",
                            "color": "#f59e0b"
                        })

        return items

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title & Summary Banner
        header = QLabel(f"<b>Skipped & Error File Audit Details</b> ({len(self.items)} Items)")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(header)

        sub = QLabel("Review the exact files skipped during scanning and their resolution status:")
        sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(sub)

        # Table Widget
        self.table = QTableWidget(len(self.items), 3, self)
        self.table.setHorizontalHeaderLabels(["Status", "File Path", "Reason / Detailed Explanation"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 280)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                gridline-color: #1e293b;
                color: #e2e8f0;
                font-size: 12px;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #38bdf8;
                font-weight: bold;
                padding: 6px;
                border: none;
            }
        """)

        for row, item in enumerate(self.items):
            # Status Badge Item
            st_item = QTableWidgetItem(item["status"])
            st_item.setTextAlignment(Qt.AlignCenter)

            # Path Item
            p_item = QTableWidgetItem(Path(item["path"]).name)
            p_item.setToolTip(item["path"])

            # Reason Item
            r_item = QTableWidgetItem(item["reason"])

            self.table.setItem(row, 0, st_item)
            self.table.setItem(row, 1, p_item)
            self.table.setItem(row, 2, r_item)

        layout.addWidget(self.table)

        # Bottom Button Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(12)

        btn_export_txt = QPushButton("📥 Export Audit Log (.txt)")
        btn_export_txt.setProperty("class", "SecondaryButton")
        btn_export_txt.setCursor(Qt.PointingHandCursor)
        btn_export_txt.setFixedHeight(38)
        btn_export_txt.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_export_txt.clicked.connect(self._export_txt_log)
        bottom_bar.addWidget(btn_export_txt)

        btn_export_json = QPushButton("📥 Export Audit Log (.json)")
        btn_export_json.setProperty("class", "SecondaryButton")
        btn_export_json.setCursor(Qt.PointingHandCursor)
        btn_export_json.setFixedHeight(38)
        btn_export_json.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_export_json.clicked.connect(self._export_json_log)
        bottom_bar.addWidget(btn_export_json)

        bottom_bar.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "PrimaryButton")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedHeight(38)
        btn_close.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 24px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(btn_close)

        layout.addLayout(bottom_bar)

    def _export_txt_log(self):
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Save Audit Log (.txt)", str(Path.home() / "scan_audit_log.txt"), "Text Files (*.txt)"
        )
        if not dest_path:
            return

        try:
            lines = [
                "==================================================",
                "       PHOTO FACE ORGANIZER - SCAN AUDIT REPORT",
                "==================================================",
                f"Scan ID: {self.summary_data.get('scan_id', 'N/A')}",
                f"Total Processed: {self.summary_data.get('total_files', 0)}",
                f"Skipped / Error Count: {len(self.items)}",
                "==================================================\n",
                "SKIPPED & ERROR FILE DETAILS:\n"
            ]

            for idx, item in enumerate(self.items, 1):
                lines.append(f"[{idx}] {item['status']}")
                lines.append(f"    Path:   {item['path']}")
                lines.append(f"    Reason: {item['reason']}\n")

            Path(dest_path).write_text("\n".join(lines), encoding="utf-8")
            QMessageBox.information(self, "Export Complete", f"Audit Log saved to:\n{dest_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save audit log: {e}")

    def _export_json_log(self):
        dest_path, _ = QFileDialog.getSaveFileName(
            self, "Save Audit Log (.json)", str(Path.home() / "scan_audit_log.json"), "JSON Files (*.json)"
        )
        if not dest_path:
            return

        try:
            export_data = {
                "scan_id": self.summary_data.get("scan_id", "N/A"),
                "total_files": self.summary_data.get("total_files", 0),
                "skipped_count": len(self.items),
                "items": self.items,
            }
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            QMessageBox.information(self, "Export Complete", f"Audit Log saved to:\n{dest_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save audit log: {e}")
