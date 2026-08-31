"""
History Page Module.

Displays historical records of previous scan runs.
Allows users to view scan results, open output folders, resume paused/interrupted scans,
rerun scan configurations, or delete metadata records without touching copied output photos.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
    """Modern History Page displaying all past scans and action controls."""

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
        self.all_scans: list[dict[str, Any]] = []

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Header Title & Top Actions
        header_l = QHBoxLayout()
        header_l.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("📜 Scan History & Run Logs")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Full audit log of previous scans. Inspect past results, resume paused runs, or manage scan records.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_title)
        header_l.addLayout(title_box)

        header_l.addStretch()

        btn_refresh = QPushButton("🔄 Refresh Log")
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setFixedHeight(36)
        btn_refresh.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_refresh.clicked.connect(self.refresh)
        header_l.addWidget(btn_refresh)

        btn_clear = QPushButton("🗑️ Clear All History")
        btn_clear.setProperty("class", "DangerButton")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setFixedHeight(36)
        btn_clear.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        btn_clear.clicked.connect(self._clear_history)
        header_l.addWidget(btn_clear)

        layout.addLayout(header_l)

        # 2. Hero Summary Stats Bar
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("background-color: #0c1322; border: 1px solid #1e293b; border-radius: 10px; padding: 10px 16px;")
        sum_l = QHBoxLayout(self.summary_card)
        sum_l.setContentsMargins(10, 6, 10, 6)
        sum_l.setSpacing(16)

        self.lbl_sum_total = QLabel("📊 Total Scans: 0")
        self.lbl_sum_total.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.lbl_sum_completed = QLabel("🟢 Completed: 0")
        self.lbl_sum_completed.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
        self.lbl_sum_photos = QLabel("📸 Photos Processed: 0")
        self.lbl_sum_photos.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 13px;")

        sum_l.addWidget(self.lbl_sum_total)
        sum_l.addWidget(self.lbl_sum_completed)
        sum_l.addWidget(self.lbl_sum_photos)
        sum_l.addStretch()
        layout.addWidget(self.summary_card)

        # 3. Filter Search Input
        self.txt_filter_history = QLineEdit()
        self.txt_filter_history.setPlaceholderText("🔍 Filter scan history records by date or status...")
        self.txt_filter_history.setStyleSheet(
            "QLineEdit { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 8px; padding: 8px 14px; font-size: 13px; color: #ffffff; font-weight: 600; }"
            "QLineEdit:focus { border: 2px solid #67e8f9; background-color: #131d33; }"
        )
        self.txt_filter_history.textChanged.connect(self._filter_history_table)
        layout.addWidget(self.txt_filter_history)

        # 4. History Table
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
            "QTableWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; color: #ffffff; outline: 0px; font-size: 13px; }"
            "QTableWidget::item { padding: 8px 12px; border-bottom: 1px solid #1e293b; }"
            "QTableWidget::item:alternate { background-color: #0f172a; }"
            "QHeaderView::section { background-color: #0f172a; color: #38bdf8; font-weight: bold; padding: 8px; border: none; }"
        )
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self):
        """Refresh scan history records and summary metrics."""
        self.table.setRowCount(0)
        self.all_scans = self.history_service.get_all_scans()

        total_scans = len(self.all_scans)
        completed_scans = 0
        total_photos = 0

        for i, s in enumerate(self.all_scans):
            self.table.insertRow(i)

            date_str = s.get("start_time", "N/A")[:16].replace("T", " ")
            status = s.get("status", "Unknown")
            tot_cnt = s.get("total_files", 0)
            matched_cnt = s.get("matched", 0)
            no_match_cnt = s.get("no_match", 0)
            duration_s = s.get("duration_seconds", 0)

            total_photos += tot_cnt
            if status == "Completed":
                completed_scans += 1

            # 0. Date Item
            d_item = QTableWidgetItem(f"📅 {date_str}")
            d_item.setForeground(QColor("#ffffff"))
            d_item.setFont(QFont("", 10, QFont.Bold))
            self.table.setItem(i, 0, d_item)

            # 1. Status Item
            status_item = QTableWidgetItem()
            if status == "Completed":
                status_item.setText("🟢 Completed")
                status_item.setForeground(QColor("#34d399"))
            elif status in {"Paused", "Interrupted"}:
                status_item.setText(f"🟡 {status}")
                status_item.setForeground(QColor("#fbbf24"))
            elif status in {"Cancelled", "Failed"}:
                status_item.setText(f"🔴 {status}")
                status_item.setForeground(QColor("#f87171"))
            else:
                status_item.setText(f"⚡ {status}")
                status_item.setForeground(QColor("#60a5fa"))
            status_item.setFont(QFont("", 10, QFont.Bold))
            self.table.setItem(i, 1, status_item)

            # 2. Total Files
            t_item = QTableWidgetItem(f"{tot_cnt} photos")
            t_item.setForeground(QColor("#ffffff"))
            self.table.setItem(i, 2, t_item)

            # 3. Matched
            m_item = QTableWidgetItem(f"{matched_cnt}")
            m_item.setForeground(QColor("#34d399"))
            self.table.setItem(i, 3, m_item)

            # 4. No Match
            nm_item = QTableWidgetItem(f"{no_match_cnt}")
            nm_item.setForeground(QColor("#f87171"))
            self.table.setItem(i, 4, nm_item)

            # 5. Duration
            dur_item = QTableWidgetItem(f"{duration_s}s")
            dur_item.setForeground(QColor("#38bdf8"))
            self.table.setItem(i, 5, dur_item)

            # 6. Action Buttons Cell
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(6, 4, 6, 4)
            cell_layout.setSpacing(6)

            scan_id = s.get("scan_id")

            btn_view = QPushButton("🎯 View Results")
            btn_view.setProperty("class", "SecondaryButton")
            btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.setFixedHeight(36)
            btn_view.setStyleSheet(
                "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
                "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
            )
            btn_view.clicked.connect(lambda _, scan_data=s: self.on_view_results_cb(scan_data))
            cell_layout.addWidget(btn_view)

            if status in {"Paused", "Interrupted", "Running"}:
                btn_resume = QPushButton("▶ Resume")
                btn_resume.setProperty("class", "PrimaryButton")
                btn_resume.setCursor(Qt.PointingHandCursor)
                btn_resume.setFixedHeight(36)
                btn_resume.setStyleSheet(
                    "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
                    "QPushButton:hover { background-color: #059669; }"
                )
                btn_resume.clicked.connect(lambda _, s_id=scan_id: self.on_resume_scan_cb(s_id))
                cell_layout.addWidget(btn_resume)

            btn_del = QPushButton("🗑️ Delete")
            btn_del.setProperty("class", "DangerButton")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedHeight(36)
            btn_del.setToolTip("Delete this scan log record")
            btn_del.setStyleSheet(
                "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 16px; font-size: 13px; font-weight: 700; }"
                "QPushButton:hover { background-color: #b91c1c; }"
            )
            btn_del.clicked.connect(lambda _, s_id=scan_id: self._delete_record(s_id))
            cell_layout.addWidget(btn_del)

            self.table.setRowHeight(i, 48)
            self.table.setCellWidget(i, 6, cell_widget)

        # Update Summary Labels
        self.lbl_sum_total.setText(f"📊 Total Scans: {total_scans}")
        self.lbl_sum_completed.setText(f"🟢 Completed: {completed_scans}")
        self.lbl_sum_photos.setText(f"📸 Photos Processed: {total_photos}")

    def _filter_history_table(self, query: str):
        q = query.strip().lower()
        for i in range(self.table.rowCount()):
            match = False
            for j in range(6):
                item = self.table.item(i, j)
                if item and q in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(i, not match)

    def _delete_record(self, scan_id: str):
        res = QMessageBox.question(
            self,
            "Delete History Record",
            "Are you sure you want to delete this scan history entry?\n\nNote: Output files in your folders will NEVER be touched.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.history_service.delete_scan_record(scan_id)
            self.refresh()

    def _clear_history(self):
        res = QMessageBox.question(
            self,
            "Clear Scan History",
            "Are you sure you want to clear all history records?\n\nOrganized photo output files will remain completely untouched.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.history_service.clear_all_history()
            self.refresh()
