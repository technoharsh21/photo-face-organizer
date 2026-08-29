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
    QScrollArea,
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
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

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

        # Hero Banner Card with Quick Actions
        actions_frame = QFrame()
        actions_frame.setStyleSheet("background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 20px;")
        actions_layout = QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(16, 16, 16, 16)
        actions_layout.setSpacing(20)

        hero_text_box = QVBoxLayout()
        hero_text_box.setSpacing(4)
        hero_title = QLabel("⚡ <b>InsightFace AI Photo Scanner</b>")
        hero_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff; border: none; background: transparent;")
        hero_sub = QLabel("Organize your photo library with 99.86% AI accuracy. Zero false matches.")
        hero_sub.setStyleSheet("color: #94a3b8; font-size: 12px; border: none; background: transparent;")
        hero_text_box.addWidget(hero_title)
        hero_text_box.addWidget(hero_sub)

        actions_layout.addLayout(hero_text_box, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        btn_new_scan = QPushButton("🚀 Standard Scan")
        btn_new_scan.setFixedHeight(38)
        btn_new_scan.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_new_scan.clicked.connect(lambda: self.navigate_cb("New Scan"))
        buttons_layout.addWidget(btn_new_scan)

        btn_solo_scan = QPushButton("🎯 Solo Scan (0% False)")
        btn_solo_scan.setFixedHeight(38)
        btn_solo_scan.setStyleSheet(
            "QPushButton { background-color: #0284c7; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #0369a1; }"
            "QPushButton:hover { background-color: #0369a1; }"
        )
        btn_solo_scan.clicked.connect(lambda: self.navigate_cb("Solo Scan"))
        buttons_layout.addWidget(btn_solo_scan)

        btn_people = QPushButton("👥 People")
        btn_people.setFixedHeight(38)
        btn_people.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_people.clicked.connect(lambda: self.navigate_cb("People"))
        buttons_layout.addWidget(btn_people)

        btn_unknowns = QPushButton("❓ Unknown Faces")
        btn_unknowns.setFixedHeight(38)
        btn_unknowns.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_unknowns.clicked.connect(lambda: self.navigate_cb("Unknown Faces"))
        buttons_layout.addWidget(btn_unknowns)

        actions_layout.addLayout(buttons_layout)
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

        layout.addStretch()
        scroll.setWidget(content)
        page_layout.addWidget(scroll)

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
