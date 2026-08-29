"""
History Page Module.

Requirements #29:
Displays full historical record of previous scan runs.
Allows users to view scan results, open output folders, resume paused/interrupted scans,
rerun scan configurations, or delete metadata records without touching copied output photos.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from services.history_service import HistoryService
from services.scan_service import ScanService


class HistoryPage(QWidget):
    """History Page displaying all past scans and actions."""

    def __init__(
        self,
        history_service: HistoryService,
        scan_service: ScanService,
        on_view_results_cb: Callable[[dict[str, Any]], None],
        on_resume_scan_cb: Callable[[str], None],
    ):
        super().__init__()
        self.history_service = history_service
        self.scan_service = scan_service
        self.on_view_results_cb = on_view_results_cb
        self.on_resume_scan_cb = on_resume_scan_cb

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        tb = QHBoxLayout()
        sub_title = QLabel("View past scan records, resume interrupted runs, inspect results, or open output folders.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        tb.addWidget(sub_title)

        tb.addStretch()

        btn_refresh = QPushButton("🔄 Refresh Log")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.clicked.connect(self.refresh)
        tb.addWidget(btn_refresh)

        btn_clear = QPushButton("🗑️ Clear History Records")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.clicked.connect(self._clear_history)
        tb.addWidget(btn_clear)

        layout.addLayout(tb)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Date / Time", "Status", "Total Files", "Matched", "No Match", "Duration", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(6, 260)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; }"
            "QTableWidget::item { padding: 8px 12px; }"
            "QTableWidget::item:alternate { background-color: #141c2e; }"
        )
        layout.addWidget(self.table, 1)

    def refresh(self):
        """Refresh scan history table."""
        self.table.setRowCount(0)
        scans = self.history_service.get_all_scans()

        for i, s in enumerate(scans):
            self.table.insertRow(i)

            date_str = s.get("start_time", "N/A")[:16].replace("T", " ")
            status = s.get("status", "Unknown")
            total = str(s.get("total_files", 0))
            matched = str(s.get("matched", 0))
            no_match = str(s.get("no_match", 0))
            duration = f"{s.get('duration_seconds', 0)}s"

            self.table.setItem(i, 0, QTableWidgetItem(date_str))

            status_item = QTableWidgetItem()
            if status == "Completed":
                status_item.setText("🟢 Completed")
            elif status in {"Paused", "Interrupted"}:
                status_item.setText(f"🟡 {status}")
            elif status in {"Cancelled", "Failed"}:
                status_item.setText(f"🔴 {status}")
            else:
                status_item.setText(f"⚡ {status}")
            self.table.setItem(i, 1, status_item)

            self.table.setItem(i, 2, QTableWidgetItem(total))
            self.table.setItem(i, 3, QTableWidgetItem(matched))
            self.table.setItem(i, 4, QTableWidgetItem(no_match))
            self.table.setItem(i, 5, QTableWidgetItem(duration))

            # Action Buttons Cell
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(6, 4, 6, 4)
            cell_layout.setSpacing(8)

            scan_id = s.get("scan_id")

            btn_view = QPushButton("🎯 View Results")
            btn_view.setProperty("class", "SecondaryButton")
            btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.setFixedHeight(28)
            btn_view.setStyleSheet("padding: 0 10px; font-weight: bold;")
            btn_view.clicked.connect(lambda _, scan_data=s: self.on_view_results_cb(scan_data))
            cell_layout.addWidget(btn_view)

            if status in {"Paused", "Interrupted", "Running"}:
                btn_resume = QPushButton("▶ Resume")
                btn_resume.setProperty("class", "PrimaryButton")
                btn_resume.setCursor(Qt.PointingHandCursor)
                btn_resume.setFixedHeight(28)
                btn_resume.setStyleSheet("padding: 0 10px; font-weight: bold;")
                btn_resume.clicked.connect(lambda _, s_id=scan_id: self.on_resume_scan_cb(s_id))
                cell_layout.addWidget(btn_resume)

            btn_del = QPushButton("🗑 Delete")
            btn_del.setProperty("class", "DangerButton")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedHeight(28)
            btn_del.setStyleSheet("padding: 0 10px; font-weight: bold;")
            btn_del.clicked.connect(lambda _, s_id=scan_id: self._delete_record(s_id))
            cell_layout.addWidget(btn_del)

            self.table.setRowHeight(i, 42)
            self.table.setCellWidget(i, 6, cell_widget)

    def _delete_record(self, scan_id: str):
        res = QMessageBox.question(
            self,
            "Delete History Metadata",
            "Are you sure you want to delete this history entry?\nNote: Output photos will NEVER be deleted.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.history_service.delete_scan_record(scan_id)
            self.refresh()

    def _clear_history(self):
        res = QMessageBox.question(
            self,
            "Clear History",
            "Clear all history records?\nOutput files will remain completely untouched.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.history_service.clear_all_history()
            self.refresh()
