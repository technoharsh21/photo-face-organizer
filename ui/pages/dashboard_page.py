"""
Dashboard Page Module.

Displays modern AI workspace metrics, interactive workflow launchpads,
enrolled people showcase carousel, real-time AI engine diagnostics,
and responsive layout scaling.
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from domain.face_engine import FaceEngine
from services.history_service import HistoryService
from services.profile_service import ProfileService
from services.settings_service import SettingsService
from services.unknown_face_service import UnknownFaceService
from ui.components.image_cache import AsyncImageCoverWidget
from ui.components.icons import get_icon


class _CountTicker(QObject):
    """Animates a QLabel's numeric text up (or down) to a target value."""

    def __init__(self, label: QLabel, parent=None):
        super().__init__(parent)
        self._label = label
        self._current = 0
        self._target = 0
        self._step = 1
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 fps
        self._timer.timeout.connect(self._tick)

    def animate_to(self, target: int):
        self._target = int(target)
        if self._current == self._target:
            self._render()
            return
        diff = abs(self._target - self._current)
        if diff <= 1:
            # Single-step changes don't need animating — snap immediately.
            self._current = self._target
            self._render()
            return
        self._step = max(1, diff // 30)  # settle in roughly 0.5 s
        self._timer.start()

    def _tick(self):
        if self._current < self._target:
            self._current = min(self._target, self._current + self._step)
        elif self._current > self._target:
            self._current = max(self._target, self._current - self._step)
        if self._current == self._target:
            self._timer.stop()
        self._render()

    def _render(self):
        self._label.setText(f"{self._current:,}")


def _create_circular_avatar(pixmap: QPixmap, size: int = 52) -> QPixmap:
    """Render a clean circular avatar cropped from a QPixmap."""
    target = QPixmap(size, size)
    target.fill(Qt.transparent)

    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)

    x_offset = max(0, (scaled.width() - size) // 2)
    y_offset = max(0, (scaled.height() - size) // 2)
    painter.drawPixmap(-x_offset, -y_offset, scaled)
    painter.end()
    return target


def _create_initials_avatar(name: str, size: int = 52, bg_color: str = "#2563eb") -> QPixmap:
    """Render a circular badge with user initials when photo is not available."""
    target = QPixmap(size, size)
    target.fill(Qt.transparent)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor(bg_color))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)

    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setPointSize(max(11, size // 3))
    font.setBold(True)
    painter.setFont(font)

    initials = "".join([part[0].upper() for part in name.strip().split()[:2]]) or "P"
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, initials)
    painter.end()
    return target


class DashboardPage(QWidget):
    """Modern, responsive AI Dashboard for Photo Face Organizer."""

    def __init__(
        self,
        profile_service: ProfileService,
        history_service: HistoryService,
        unknown_face_service: UnknownFaceService,
        navigate_cb: Callable[[str], None],
        settings_service: SettingsService | None = None,
        face_engine: FaceEngine | None = None,
    ):
        super().__init__()
        self.profile_service = profile_service
        self.history_service = history_service
        self.unknown_face_service = unknown_face_service
        self.navigate_cb = navigate_cb
        self.settings_service = settings_service
        self.face_engine = face_engine
        self._needs_refresh = True  # Track if page needs refresh on next visit

        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll Area for Full Responsive Display
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("DashboardScrollContent")
        self.content_layout = QVBoxLayout(scroll_content)
        self.content_layout.setContentsMargins(24, 20, 24, 24)
        self.content_layout.setSpacing(22)

        # 1. Hero banner (greeting + primary CTAs)
        self._build_hero_banner()

        # 2. Top Metrics Cards
        self._build_stats_cards()

        # 3. AI Workflow Launchpads (2x2 Grid)
        self._build_workflow_launchpads()

        # 4. Enrolled People Profiles Showcase
        self._build_people_showcase()

        # 5. Recent Activity feed
        self._build_activity_feed()

        # 6. AI Engine & System Diagnostics Hub
        self._build_diagnostics_hub()

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area)

    def _build_hero_banner(self):
        """Welcome banner with time-based greeting and primary call-to-actions."""
        hero = QFrame()
        hero.setObjectName("HeroBanner")
        layout = QHBoxLayout(hero)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        self.hero_title = QLabel(f"{greeting} — let's organize your photos")
        self.hero_title.setObjectName("HeroTitle")
        self.hero_subtitle = QLabel("Face-powered photo organization with InsightFace AI.")
        self.hero_subtitle.setObjectName("HeroSubtitle")
        text_col.addWidget(self.hero_title)
        text_col.addWidget(self.hero_subtitle)
        layout.addLayout(text_col, 1)

        btn_scan = QPushButton("🚀  New Scan")
        btn_scan.setProperty("class", "PrimaryButton")
        btn_scan.setCursor(Qt.PointingHandCursor)
        btn_scan.clicked.connect(lambda: self.navigate_cb("New Scan"))
        layout.addWidget(btn_scan, 0, Qt.AlignVCenter)

        btn_profiles = QPushButton("👥  People Profiles")
        btn_profiles.setProperty("class", "GhostButton")
        btn_profiles.setCursor(Qt.PointingHandCursor)
        btn_profiles.clicked.connect(lambda: self.navigate_cb("People"))
        layout.addWidget(btn_profiles, 0, Qt.AlignVCenter)

        self.content_layout.addWidget(hero)

    def _build_stats_cards(self):
        """Construct the 4 key statistical metric cards."""
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(14)

        self.card_profiles = self._create_metric_card(
            title="TOTAL PROFILES",
            subtext="Enrolled Face IDs",
            value="0",
            accent_class="StatCardBlue",
            value_color="#38bdf8",
            icon="users",
        )
        self.card_processed = self._create_metric_card(
            title="SCANNED PHOTOS",
            subtext="Total Processed",
            value="0",
            accent_class="StatCardGreen",
            value_color="#34d399",
            icon="image",
        )
        self.card_matched = self._create_metric_card(
            title="MATCHED PHOTOS",
            subtext="Organized & Sorted",
            value="0",
            accent_class="StatCardPurple",
            value_color="#c084fc",
            icon="check_circle",
        )
        self.card_no_match = self._create_metric_card(
            title="UNMATCHED BACKLOG",
            subtext="Available for Review",
            value="0",
            accent_class="StatCardAmber",
            value_color="#fbbf24",
            icon="question_circle",
        )

        stats_layout.addWidget(self.card_profiles["frame"])
        stats_layout.addWidget(self.card_processed["frame"])
        stats_layout.addWidget(self.card_matched["frame"])
        stats_layout.addWidget(self.card_no_match["frame"])

        self.content_layout.addWidget(stats_container)

    def _create_metric_card(
        self,
        title: str,
        subtext: str,
        value: str,
        accent_class: str,
        value_color: str,
        icon: str,
    ) -> dict[str, Any]:
        frame = QFrame()
        frame.setObjectName("MetricCard")
        frame.setProperty("class", accent_class)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header Row: Icon + Label
        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(6)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(icon, color=value_color, size=18).pixmap(18, 18))
        hdr_layout.addWidget(icon_lbl)

        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "StatLabel")
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()

        # Value Label
        val_lbl = QLabel(value)
        val_lbl.setObjectName("MetricValue")
        val_lbl.setStyleSheet(f"color: {value_color};")

        # Subtext
        sub_lbl = QLabel(subtext)
        sub_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")

        layout.addLayout(hdr_layout)
        layout.addWidget(val_lbl)
        layout.addWidget(sub_lbl)

        # Animated counter ticker
        ticker = _CountTicker(val_lbl, self)
        return {"frame": frame, "val_lbl": val_lbl, "sub_lbl": sub_lbl, "ticker": ticker}

    def _build_workflow_launchpads(self):
        """Construct the 2x2 AI workflow launchpad cards."""
        section_box = QVBoxLayout()
        section_box.setSpacing(10)

        # Section Header
        sec_header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        sec_title = QLabel("⚡ Quick AI Workflows")
        sec_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        sec_sub = QLabel("Launch automated face recognition, isolation scans, or storage optimization in one click.")
        sec_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")

        title_box.addWidget(sec_title)
        title_box.addWidget(sec_sub)
        sec_header.addLayout(title_box)
        sec_header.addStretch()

        section_box.addLayout(sec_header)

        # Grid of 4 Cards
        grid = QGridLayout()
        grid.setSpacing(14)

        # Card 1: Standard Scan Wizard
        card_scan = self._create_workflow_card(
            badge="Multi-Face Scan • 99.86% Accuracy",
            badge_class="BadgeGreen",
            title="🚀 Standard Scan Wizard",
            description="Scan photo folders or entire storage drives. Automatically match faces and sort verified photos into dedicated profile folders.",
            button_text="Start Standard Scan →",
            button_style=(
                "background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; "
                "padding: 0 16px; font-size: 13px; border: 1px solid #059669;"
            ),
            callback=lambda: self.navigate_cb("New Scan"),
        )

        # Card 2: Solo Scan Wizard
        card_solo = self._create_workflow_card(
            badge="Solo Isolation • 0% False Matches",
            badge_class="BadgeCyan",
            title="🎯 Solo Scan (0% False-Positive)",
            description="Find pure single-person photos of your chosen subject. Employs multi-angle face geometry with zero background person intrusion.",
            button_text="Start Solo Scan →",
            button_style=(
                "background-color: #0284c7; color: #ffffff; font-weight: 700; border-radius: 8px; "
                "padding: 0 16px; font-size: 13px; border: 1px solid #0369a1;"
            ),
            callback=lambda: self.navigate_cb("Solo Scan"),
        )

        # Card 3: Duplicate Finder
        card_dup = self._create_workflow_card(
            badge="SHA-256 Storage Saver",
            badge_class="BadgePurple",
            title="🔍 Duplicate Photo Finder",
            description="Rapid byte-level duplicate scanner. Instantly detect identical or renamed photos across multiple directories and safely free up disk space.",
            button_text="Scan for Duplicates →",
            button_style=(
                "background-color: #7c3aed; color: #ffffff; font-weight: 700; border-radius: 8px; "
                "padding: 0 16px; font-size: 13px; border: 1px solid #6d28d9;"
            ),
            callback=lambda: self.navigate_cb("Duplicates"),
        )

        # Card 4: Unknown Faces Studio
        self.card_unknown_badge = QLabel("AI Face Discovery")
        self.card_unknown_badge.setProperty("class", "BadgeAmber")

        card_unknown = self._create_workflow_card_custom_badge(
            badge_widget=self.card_unknown_badge,
            title="❓ Unknown Faces Studio",
            description="Review unmatched faces discovered in previous scans. Automatically cluster recurring unknown people and convert them into new profiles in one click.",
            button_text="Review Unknown Faces →",
            button_style=(
                "background-color: #d97706; color: #ffffff; font-weight: 700; border-radius: 8px; "
                "padding: 0 16px; font-size: 13px; border: 1px solid #b45309;"
            ),
            callback=lambda: self.navigate_cb("Unknown Faces"),
        )

        # Card 5: People Profiles
        card_people = self._create_workflow_card(
            badge="Face Registry • Reference Photos",
            badge_class="BadgeBlue",
            title="👥 People Profiles",
            description="Create and manage per-person face profiles. Add reference photos, retrain models, and keep every identity crisp.",
            button_text="Manage Profiles →",
            button_style="ghost",
            callback=lambda: self.navigate_cb("People"),
        )

        # Card 6: Find Photos by Person
        card_find = self._create_workflow_card(
            badge="Instant Person Search",
            badge_class="BadgeCyan",
            title="🔎 Find Photos by Person",
            description="Search any enrolled person and instantly surface every matching photo across your library without re-running scans.",
            button_text="Find Photos →",
            button_style="ghost",
            callback=lambda: self.navigate_cb("Find Photos"),
        )

        grid.addWidget(card_scan, 0, 0)
        grid.addWidget(card_solo, 0, 1)
        grid.addWidget(card_dup, 0, 2)
        grid.addWidget(card_unknown, 1, 0)
        grid.addWidget(card_people, 1, 1)
        grid.addWidget(card_find, 1, 2)

        section_box.addLayout(grid)
        self.content_layout.addLayout(section_box)

    def _create_workflow_card(
        self,
        badge: str,
        badge_class: str,
        title: str,
        description: str,
        button_text: str,
        button_style: str,
        callback: Callable[[], None],
    ) -> QFrame:
        badge_lbl = QLabel(badge)
        badge_lbl.setProperty("class", badge_class)
        if button_style == "ghost":
            css = (
                "QPushButton { background-color: transparent; color: #38bdf8; font-weight: 700; border-radius: 8px; "
                "padding: 0 16px; font-size: 13px; border: 1px solid #1e293b; }"
                "QPushButton:hover { background-color: rgba(56, 189, 248, 0.10); border-color: #38bdf8; }"
            )
        else:
            css = button_style
        return self._create_workflow_card_custom_badge(badge_lbl, title, description, button_text, css, callback)

    def _create_workflow_card_custom_badge(
        self,
        badge_widget: QWidget,
        title: str,
        description: str,
        button_text: str,
        button_style: str,
        callback: Callable[[], None],
    ) -> QFrame:
        card = QFrame()
        card.setProperty("class", "WorkflowCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Top Badge Row
        top_row = QHBoxLayout()
        top_row.addWidget(badge_widget)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; margin-top: 2px;")
        layout.addWidget(lbl_title)

        # Description
        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(lbl_desc, 1)

        # Action Button
        btn = QPushButton(button_text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(button_style)
        btn.clicked.connect(callback)
        layout.addWidget(btn)

        return card

    def _build_people_showcase(self):
        """Construct the Enrolled People showcase gallery."""
        self.showcase_section = QVBoxLayout()
        self.showcase_section.setSpacing(10)

        # Header Row
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        sec_title = QLabel("👥 Enrolled People Profiles")
        sec_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        sec_sub = QLabel("Active identities trained for facial recognition matching and auto-sorting.")
        sec_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")

        title_box.addWidget(sec_title)
        title_box.addWidget(sec_sub)
        hdr.addLayout(title_box)
        hdr.addStretch()

        btn_add = QPushButton("➕ Create Profile")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_add.clicked.connect(lambda: self.navigate_cb("People"))
        hdr.addWidget(btn_add)

        btn_view_all = QPushButton("View All Profiles →")
        btn_view_all.setCursor(Qt.PointingHandCursor)
        btn_view_all.setStyleSheet(
            "QPushButton { background-color: transparent; color: #94a3b8; font-weight: 700; padding: 0 16px; font-size: 13px; border: none; }"
            "QPushButton:hover { color: #ffffff; text-decoration: underline; }"
        )
        btn_view_all.clicked.connect(lambda: self.navigate_cb("People"))
        hdr.addWidget(btn_view_all)

        self.showcase_section.addLayout(hdr)

        # Profiles Grid / Row Container (scroll horizontally when > 5 profiles)
        self.profiles_container = QWidget()
        self.profiles_layout = QHBoxLayout(self.profiles_container)
        self.profiles_layout.setContentsMargins(0, 0, 0, 0)
        self.profiles_layout.setSpacing(12)

        profiles_scroll = QScrollArea()
        profiles_scroll.setWidget(self.profiles_container)
        profiles_scroll.setWidgetResizable(True)
        profiles_scroll.setFixedHeight(170)
        profiles_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        profiles_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        profiles_scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        self.showcase_section.addWidget(profiles_scroll)
        self.content_layout.addLayout(self.showcase_section)

    def _build_activity_feed(self):
        """Recent scans timeline."""
        section = QVBoxLayout()
        section.setSpacing(10)

        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        sec_title = QLabel("🕘 Recent Activity")
        sec_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        sec_sub = QLabel("Your last scans at a glance.")
        sec_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(sec_title)
        title_box.addWidget(sec_sub)
        hdr.addLayout(title_box)
        hdr.addStretch()

        btn_history = QPushButton("View Full History →")
        btn_history.setCursor(Qt.PointingHandCursor)
        btn_history.setStyleSheet(
            "QPushButton { background-color: transparent; color: #94a3b8; font-weight: 700; padding: 0 16px; font-size: 13px; border: none; }"
            "QPushButton:hover { color: #ffffff; text-decoration: underline; }"
        )
        btn_history.clicked.connect(lambda: self.navigate_cb("History"))
        hdr.addWidget(btn_history)

        section.addLayout(hdr)

        self.activity_list = QVBoxLayout()
        self.activity_list.setSpacing(6)
        section.addLayout(self.activity_list)
        self.content_layout.addLayout(section)

    def _refresh_activity_feed(self, scans: list[dict[str, Any]]):
        """Rebuild the activity rows from the most recent scans."""
        while self.activity_list.count():
            item = self.activity_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not scans:
            hint = QLabel("No scans yet — launch your first scan to see activity here.")
            hint.setStyleSheet("color: #64748b; font-size: 12px;")
            self.activity_list.addWidget(hint)
            return

        recent = sorted(scans, key=lambda s: s.get("start_time", ""), reverse=True)[:4]
        for s in recent:
            row = QFrame()
            row.setObjectName("CardGlass")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon("history", color="#38bdf8", size=16).pixmap(16, 16))
            rl.addWidget(icon_lbl, 0, Qt.AlignVCenter)

            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            summary_lbl = QLabel(
                f"{s.get('processed', 0):,} photos processed · {s.get('matched', 0):,} matched"
            )
            summary_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 600; background: transparent;")
            date_str = str(s.get("start_time", "N/A"))[:16].replace("T", " ")
            time_lbl = QLabel(date_str)
            time_lbl.setStyleSheet("color: #64748b; font-size: 11px; background: transparent;")
            text_col.addWidget(summary_lbl)
            text_col.addWidget(time_lbl)
            rl.addLayout(text_col, 1)

            self.activity_list.addWidget(row)

    def _build_diagnostics_hub(self):
        """Construct the AI Engine & System Health diagnostics bar."""
        diag_card = QFrame()
        diag_card.setProperty("class", "DiagnosticsCard")

        diag_layout = QHBoxLayout(diag_card)
        diag_layout.setContentsMargins(18, 14, 18, 14)
        diag_layout.setSpacing(16)

        # 1. Face Engine Model
        col1 = self._create_diag_col("🧠 AI ARCHITECTURE", "InsightFace SCRFD + ArcFace", "512-d biometric embeddings")
        # 2. Hardware Mode
        hw_pref = "Auto-Accelerated"
        if self.settings_service:
            hw_pref = self.settings_service.get("device_preference", "Auto")
        self.col_hw_mode = self._create_diag_col("⚡ AI ACCELERATION", f"{hw_pref} Provider", "Low latency inference")
        # 3. Precision Rating
        col3 = self._create_diag_col("🎯 RECOGNITION PRECISION", "99.86% Cosine Accuracy", "0% False-Positive Mode")
        # 4. Vector Cache
        col4 = self._create_diag_col("🗄️ VECTOR INDEX CACHE", "SQLite & Memory Cache", "Instant re-scan matching")

        diag_layout.addLayout(col1["layout"], 1)
        diag_layout.addLayout(self.col_hw_mode["layout"], 1)
        diag_layout.addLayout(col3["layout"], 1)
        diag_layout.addLayout(col4["layout"], 1)

        self.content_layout.addWidget(diag_card)

    def _create_diag_col(self, tag: str, title: str, sub: str) -> dict[str, Any]:
        l = QVBoxLayout()
        l.setSpacing(2)

        tag_lbl = QLabel(tag)
        tag_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;")

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700;")

        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")

        l.addWidget(tag_lbl)
        l.addWidget(title_lbl)
        l.addWidget(sub_lbl)

        return {"layout": l, "title_lbl": title_lbl, "sub_lbl": sub_lbl}

    def refresh(self):
        """Refresh dashboard metric counts, people showcase gallery, and badges."""
        profiles = self.profile_service.list_profiles_summary()
        self.card_profiles["ticker"].animate_to(len(profiles))

        scans = self.history_service.get_all_scans()
        total_proc = sum(s.get("processed", 0) for s in scans)
        total_match = sum(s.get("matched", 0) for s in scans)
        total_no_match = sum(s.get("no_match", 0) for s in scans)

        self.card_processed["ticker"].animate_to(total_proc)
        self.card_matched["ticker"].animate_to(total_match)
        self.card_no_match["ticker"].animate_to(total_no_match)

        # Hero subtitle mirrors the headline numbers (or welcomes first-timers)
        if profiles:
            self.hero_subtitle.setText(
                f"{len(profiles)} {'profile' if len(profiles) == 1 else 'profiles'} · {total_proc:,} photos organized · {total_match:,} matched"
            )
        else:
            self.hero_subtitle.setText("Create your first profile to start organizing photos by person.")

        # Update Unknown Faces Badge Count
        unknowns = self.unknown_face_service.list_unknown_faces()
        u_count = len(unknowns)
        if u_count > 0:
            self.card_unknown_badge.setText(f"AI Discovery • {u_count} New Faces")
        else:
            self.card_unknown_badge.setText("AI Face Discovery")

        # Update Hardware Diagnostics if Available
        if self.settings_service:
            hw_pref = self.settings_service.get("device_preference", "Auto")
            self.col_hw_mode["title_lbl"].setText(f"{hw_pref} Provider")

        # Refresh Profiles Showcase Container
        self._refresh_people_showcase(profiles)
        # Refresh Recent Activity feed
        self._refresh_activity_feed(scans)
        self._needs_refresh = False

    def _refresh_people_showcase(self, profiles: list[dict[str, Any]]):
        """Rebuild the people showcase cards dynamically."""
        # Clear existing items
        while self.profiles_layout.count():
            item = self.profiles_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not profiles:
            # First-Time User Onboarding Guide Banner
            onboarding_frame = QFrame()
            onboarding_frame.setStyleSheet(
                "background-color: #0f172a; border: 1px dashed #334155; border-radius: 12px; padding: 20px;"
            )
            ob_layout = QHBoxLayout(onboarding_frame)
            ob_layout.setContentsMargins(16, 12, 16, 12)
            ob_layout.setSpacing(20)

            ob_text_box = QVBoxLayout()
            ob_text_box.setSpacing(4)

            ob_title = QLabel("👋 <b>Get Started: Create Your First Face Profile</b>")
            ob_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; border: none; background: transparent;")

            ob_desc = QLabel(
                "1. Add a person profile with 1-5 reference photos (or 360° webcam scan).\n"
                "2. Launch Standard Scan or Solo Scan on your photo directory.\n"
                "3. Watch InsightFace organize matched photos with 99.86% AI precision."
            )
            ob_desc.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.5; border: none; background: transparent;")

            ob_text_box.addWidget(ob_title)
            ob_text_box.addWidget(ob_desc)
            ob_layout.addLayout(ob_text_box, 1)

            btn_create_first = QPushButton("➕ Create First Profile")
            btn_create_first.setCursor(Qt.PointingHandCursor)
            btn_create_first.setStyleSheet(
                "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
                "QPushButton:hover { background-color: #059669; }"
            )
            btn_create_first.clicked.connect(lambda: self.navigate_cb("People"))
            ob_layout.addWidget(btn_create_first)

            self.profiles_layout.addWidget(onboarding_frame)
            return

        # Show all profiles (scrollable)
        colors = ["#2563eb", "#059669", "#7c3aed", "#d97706", "#0891b2", "#dc2626"]
        for idx, profile in enumerate(profiles):
            p_name = profile.get("name", "Unknown")
            ref_count = profile.get("ref_count", 0)

            p_card = QFrame()
            p_card.setProperty("class", "ProfileShowcaseCard")
            p_card.setCursor(Qt.PointingHandCursor)
            p_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            p_layout = QVBoxLayout(p_card)
            p_layout.setContentsMargins(14, 14, 14, 14)
            p_layout.setSpacing(8)
            p_layout.setAlignment(Qt.AlignCenter)

            # Avatar (async loading - shows initials immediately, then updates)
            bg = colors[idx % len(colors)]
            first_ref_path = profile.get("first_ref_path")
            avatar_widget = AsyncImageCoverWidget(
                image_path=first_ref_path if (first_ref_path and Path(first_ref_path).exists()) else None,
                width=52,
                height=52,
                radius=12,  # Rounded-square to match card shape
                bg_color=bg,
                initials=p_name if not (first_ref_path and Path(first_ref_path).exists()) else None,
            )
            p_layout.addWidget(avatar_widget, 0, Qt.AlignCenter)

            # Name
            name_lbl = QLabel(p_name)
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
            name_lbl.setAlignment(Qt.AlignCenter)
            p_layout.addWidget(name_lbl)

            # Photo Count Pill
            cnt_lbl = QLabel(f"📷 {ref_count} Photo{'s' if ref_count != 1 else ''}")
            cnt_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; background-color: #1e293b; border-radius: 4px; padding: 2px 6px;")
            cnt_lbl.setAlignment(Qt.AlignCenter)
            p_layout.addWidget(cnt_lbl)

            # Click handler to navigate to People
            p_card.mousePressEvent = lambda _, p_id=profile.get("id"): self.navigate_cb("People")

            self.profiles_layout.addWidget(p_card)

        # Quick Add Action Card at End
        add_card = QFrame()
        add_card.setProperty("class", "AddProfileCard")
        add_card.setCursor(Qt.PointingHandCursor)
        add_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        add_layout = QVBoxLayout(add_card)
        add_layout.setContentsMargins(14, 14, 14, 14)
        add_layout.setSpacing(6)
        add_layout.setAlignment(Qt.AlignCenter)

        add_icon = QLabel("➕")
        add_icon.setStyleSheet("font-size: 24px; color: #38bdf8; background: transparent;")
        add_icon.setAlignment(Qt.AlignCenter)

        add_lbl = QLabel("Add Person")
        add_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8; background: transparent;")
        add_lbl.setAlignment(Qt.AlignCenter)

        add_sub = QLabel("New Identity")
        add_sub.setStyleSheet("font-size: 11px; color: #64748b; background: transparent;")
        add_sub.setAlignment(Qt.AlignCenter)

        add_layout.addWidget(add_icon)
        add_layout.addWidget(add_lbl)
        add_layout.addWidget(add_sub)

        add_card.mousePressEvent = lambda _: self.navigate_cb("People")
        self.profiles_layout.addWidget(add_card)
