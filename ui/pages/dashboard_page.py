"""
Dashboard Page Module.

Displays application summary statistics, recent scans list, quick actions,
and empty states for non-technical users.
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.history_service import HistoryService
from services.profile_service import ProfileService
from services.unknown_face_service import UnknownFaceService


class DashboardPage(QWidget):
    """Dashboard Page displaying real metrics, recent scans, and quick actions."""

    def __init__(
        self,
        profile_service: ProfileService,
        history_service: HistoryService,
        unknown_face_service: UnknownFaceService,
        navigate_cb: Callable[[str], None],
    ):
        super().__init__()
        self.profile_service = profile_service
        self.history_service = history_service
        self.unknown_face_service = unknown_face_service
        self.navigate_cb = navigate_cb

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("Dashboard")
        header.setProperty("class", "PageHeader")
        layout.addWidget(header)

        # Stats Cards Grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.card_profiles = self._create_stat_card("Total Profiles", "0", "#3b82f6")
        self.card_processed = self._create_stat_card("Processed Photos", "0", "#10b981")
        self.card_matched = self._create_stat_card("Matched Photos", "0", "#8b5cf6")
        self.card_no_match = self._create_stat_card("No Match Photos", "0", "#f59e0b")

        stats_layout.addWidget(self.card_profiles["frame"])
        stats_layout.addWidget(self.card_processed["frame"])
        stats_layout.addWidget(self.card_matched["frame"])
        stats_layout.addWidget(self.card_no_match["frame"])

        layout.addLayout(stats_layout)

        # Quick Actions Bar
        actions_frame = QFrame()
        actions_frame.setProperty("class", "Card")
        actions_layout = QHBoxLayout(actions_frame)

        act_title = QLabel("Quick Actions:")
        act_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        actions_layout.addWidget(act_title)

        btn_new_scan = QPushButton("🚀 Start New Scan")
        btn_new_scan.setProperty("class", "PrimaryButton")
        btn_new_scan.clicked.connect(lambda: self.navigate_cb("New Scan"))
        actions_layout.addWidget(btn_new_scan)

        btn_people = QPushButton("👥 Manage People")
        btn_people.setProperty("class", "SecondaryButton")
        btn_people.clicked.connect(lambda: self.navigate_cb("People"))
        actions_layout.addWidget(btn_people)

        btn_unknowns = QPushButton("❓ Unknown Faces")
        btn_unknowns.setProperty("class", "SecondaryButton")
        btn_unknowns.clicked.connect(lambda: self.navigate_cb("Unknown Faces"))
        actions_layout.addWidget(btn_unknowns)

        actions_layout.addStretch()
        layout.addWidget(actions_frame)

        # Recent Scans Section
        scans_header = QLabel("Recent Scans")
        scans_header.setProperty("class", "SectionHeader")
        layout.addWidget(scans_header)

        self.scans_list = QListWidget()
        layout.addWidget(self.scans_list)

        self.empty_label = QLabel("No scan history found. Create people and run your first scan!")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #a0a0b0; font-size: 14px; margin: 30px;")
        layout.addWidget(self.empty_label)

    def _create_stat_card(self, label_text: str, value_text: str, color: str) -> dict:
        frame = QFrame()
        frame.setProperty("class", "Card")
        l = QVBoxLayout(frame)

        val = QLabel(value_text)
        val.setProperty("class", "StatValue")
        val.setStyleSheet(f"color: {color};")
        lbl = QLabel(label_text)
        lbl.setProperty("class", "StatLabel")

        l.addWidget(val)
        l.addWidget(lbl)

        return {"frame": frame, "value_label": val}

    def refresh(self):
        """Refresh dashboard statistics and recent scans list."""
        profiles = self.profile_service.list_profiles()
        self.card_profiles["value_label"].setText(str(len(profiles)))

        scans = self.history_service.get_all_scans()

        total_proc = sum(s.get("processed", 0) for s in scans)
        total_match = sum(s.get("matched", 0) for s in scans)
        total_no_match = sum(s.get("no_match", 0) for s in scans)

        self.card_processed["value_label"].setText(str(total_proc))
        self.card_matched["value_label"].setText(str(total_match))
        self.card_no_match["value_label"].setText(str(total_no_match))

        self.scans_list.clear()
        if scans:
            self.empty_label.hide()
            self.scans_list.show()
            for s in scans[:5]:  # Top 5 recent scans
                s_id = s.get("scan_id", "Unknown")[:8]
                date_str = s.get("start_time", "N/A")[:16].replace("T", " ")
                status = s.get("status", "Unknown")
                total = s.get("total_files", 0)
                matched = s.get("matched", 0)
                txt = f"Scan #{s_id} | {date_str} | Status: {status} | Processed: {total} | Matched: {matched}"
                item = QListWidgetItem(txt)
                self.scans_list.addItem(item)
        else:
            self.scans_list.hide()
            self.empty_label.show()
