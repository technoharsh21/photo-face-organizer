"""
People (Profiles) Management Page Module.

Allows users to create, rename, and delete profiles, view reference photos in a responsive
2D auto-reflowing grid that fills 100% of the horizontal space with edge-to-edge photo covers,
multi-select photos for batch deletion, add reference photos, batch train from folders, and clean outliers.
"""

from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from domain.face_engine import FaceEngine
from services.profile_service import ProfileService
from ui.components.face_selector import FaceSelectorDialog
from ui.components.live_face_scanner_dialog import LiveFaceScannerDialog


class ImageCoverWidget(QWidget):
    """Renders an image filled edge-to-edge (object-fit: cover) with rounded corners and zero black letterbox borders."""

    def __init__(
        self,
        image_path: str | None = None,
        width: int | None = None,
        height: int = 120,
        radius: int = 8,
        parent=None,
    ):
        super().__init__(parent)
        self.image_path = image_path
        self.radius = radius
        self.initials: str | None = None
        self.bg_color: str = "#2563eb"
        self.pixmap: QPixmap | None = None

        if width:
            self.setFixedSize(width, height)
        else:
            self.setFixedHeight(height)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if image_path and Path(image_path).exists():
            self.pixmap = QPixmap(str(image_path))

    def set_image_path(self, path: str | None):
        self.image_path = path
        self.initials = None
        if path and Path(path).exists():
            self.pixmap = QPixmap(str(path))
        else:
            self.pixmap = None
        self.update()

    def set_initials(self, name: str, bg_color: str = "#2563eb"):
        self.pixmap = None
        self.image_path = None
        self.initials = "".join([part[0].upper() for part in name.strip().split()[:2]]) or "P"
        self.bg_color = bg_color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w = self.width()
        h = self.height()

        if self.pixmap and not self.pixmap.isNull():
            # True center crop (object-fit: cover) to eliminate any letterbox black borders
            scaled = self.pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, self.radius, self.radius)
            painter.setClipPath(path)
            x_off = max(0, (scaled.width() - w) // 2)
            y_off = max(0, (scaled.height() - h) // 2)
            painter.drawPixmap(-x_off, -y_off, scaled)
        elif self.initials:
            painter.setBrush(QColor(self.bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, self.radius, self.radius)
            painter.setPen(QColor("#ffffff"))
            font = painter.font()
            font.setPointSize(max(12, h // 3))
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self.initials)
        else:
            painter.setBrush(QColor("#080c14"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, self.radius, self.radius)
            painter.setPen(QColor("#64748b"))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "📷 Photo")
        painter.end()


class ProfileListItemWidget(QWidget):
    """Rich, spacious visual list item card for the profile navigator sidebar."""

    def __init__(self, name: str, ref_count: int, avatar_path: str | None, is_group: bool = False, bg_color: str = "#2563eb"):
        super().__init__()
        self.profile_name = name
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # Edge-to-edge Avatar Thumbnail (44x44 rounded-square)
        self.avatar_cover = ImageCoverWidget(avatar_path, width=44, height=44, radius=10)
        self.avatar_cover.setCursor(Qt.PointingHandCursor)
        if not (avatar_path and Path(avatar_path).exists()):
            self.avatar_cover.set_initials(name, bg_color=bg_color)
        layout.addWidget(self.avatar_cover)

        # Info Box with prominent, clear typography
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff; background: transparent; border: none;")
        name_lbl.setCursor(Qt.PointingHandCursor)

        sub_text = f"📷 {ref_count} reference photo{'s' if ref_count != 1 else ''}"
        if is_group:
            sub_text = f"👥 Group • {sub_text}"

        sub_lbl = QLabel(sub_text)
        sub_lbl.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent; border: none;")
        sub_lbl.setCursor(Qt.PointingHandCursor)

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(sub_lbl)
        layout.addLayout(info_layout, 1)


class ReferencePhotoCard(QFrame):
    """Interactive reference photo card with edge-to-edge photo, checkbox overlay, rating badge, and classic red remove button."""

    def __init__(
        self,
        ref: dict[str, Any],
        is_selected: bool,
        on_toggle: Any,
        on_delete: Any,
    ):
        super().__init__()
        self.ref_id = ref.get("id")
        self.is_selected = is_selected
        self.on_toggle = on_toggle
        self.on_delete = on_delete

        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumWidth(130)
        self.setMaximumWidth(260)
        self.setFixedHeight(198)

        self._update_card_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        # Full-size Edge-to-Edge Image Cover (Zero black letterbox side bars)
        stored_path = ref.get("stored_path")
        self.img_cover = ImageCoverWidget(stored_path, height=120, radius=8)
        self.img_cover.setCursor(Qt.PointingHandCursor)

        # Overlay Checkbox pinned to top-left of image
        self.chk = QCheckBox(self.img_cover)
        self.chk.setFixedSize(18, 18)
        self.chk.setChecked(is_selected)
        self.chk.setCursor(Qt.PointingHandCursor)
        self.chk.setToolTip("Select for multi-delete")
        self.chk.move(6, 6)
        self.chk.setStyleSheet(
            "QCheckBox { background: transparent; border: none; padding: 0px; margin: 0px; }"
            "QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #38bdf8; background-color: rgba(15, 23, 42, 0.9); }"
            "QCheckBox::indicator:checked { background-color: #ef4444; border: 1px solid #ef4444; }"
        )
        self.chk.toggled.connect(self._on_chk_toggled)

        layout.addWidget(self.img_cover)

        # Quality Rating (Gold stars)
        q_info = ref.get("quality", {})
        q_stars = q_info.get("stars", 5) if isinstance(q_info, dict) else 5
        q_badge = "⭐" * q_stars

        q_lbl = QLabel(f"{q_badge} {q_stars}/5")
        q_lbl.setStyleSheet("font-size: 10px; color: #fbbf24; font-weight: bold; background: transparent; border: none;")
        q_lbl.setAlignment(Qt.AlignCenter)
        q_lbl.setCursor(Qt.PointingHandCursor)
        layout.addWidget(q_lbl)

        # Classic Solid Red Remove Button
        btn_del = QPushButton("🗑 Remove")
        btn_del.setProperty("class", "DangerButton")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setFixedHeight(24)
        btn_del.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; font-weight: 700; border-radius: 6px; font-size: 11px; padding: 0 6px; border: none; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        btn_del.clicked.connect(lambda: self.on_delete(self.ref_id))
        layout.addWidget(btn_del)

    def _on_chk_toggled(self, checked: bool):
        self.is_selected = checked
        self._update_card_style()
        self.on_toggle(self.ref_id, checked)

    def _update_card_style(self):
        if self.is_selected:
            self.setStyleSheet(
                "QFrame { background-color: #231114; border: 2px solid #ef4444; border-radius: 10px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 10px; }"
                "QFrame:hover { border: 1px solid #38bdf8; }"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.chk.setChecked(not self.chk.isChecked())
        super().mousePressEvent(event)


class ResponsiveReferenceGrid(QWidget):
    """Fluid 2D reference photo grid that dynamically reflows and stretches cards to fill 100% width."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.cards: list[QWidget] = []

    def set_cards(self, cards: list[QWidget]):
        self.clear()
        self.cards = cards
        self.relayout()

    def clear(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.cards = []

    def relayout(self):
        if not self.cards:
            return

        # Target card column width is ~175px (larger, crisper card display)
        container_w = max(240, self.width())
        cols = max(2, container_w // 175)

        # Reset all column stretches
        for c in range(24):
            self.grid_layout.setColumnStretch(c, 0)

        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        # Set column stretch = 1 on all active columns so cards expand evenly to fill 100% of width
        for c in range(cols):
            self.grid_layout.setColumnStretch(c, 1)

        for idx, card in enumerate(self.cards):
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.relayout()


class PeoplePage(QWidget):
    """Modern, responsive People Profiles Studio & Biometric Registry."""

    def __init__(self, profile_service: ProfileService, face_engine: FaceEngine | None = None):
        super().__init__()
        self.profile_service = profile_service
        self.face_engine = face_engine or getattr(profile_service, "face_engine", None)
        self.current_profile_id: str | None = None
        self.selected_ref_ids: set[str] = set()
        self.worker: ProfileBatchTrainWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        # 1. Clean Top Header
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        page_title = QLabel("👥 People Profiles & Biometric Registry")
        page_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        sub_title = QLabel("Manage reference photos, multi-angle face embeddings, and recognition settings.")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(page_title)
        title_box.addWidget(sub_title)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        btn_add_person = QPushButton("➕ Create Profile")
        btn_add_person.setProperty("class", "PrimaryButton")
        btn_add_person.setCursor(Qt.PointingHandCursor)
        btn_add_person.setFixedHeight(36)
        btn_add_person.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 16px; font-size: 13px; border: 1px solid #059669; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_add_person.clicked.connect(self._create_profile)
        top_bar.addWidget(btn_add_person)

        root_layout.addLayout(top_bar)

        # 2. Main Horizontal Splitter (Spacious left sidebar)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Profile Navigator (Larger width for person list)
        left_widget = QFrame()
        left_widget.setProperty("class", "Card")
        left_widget.setMinimumWidth(260)
        left_widget.setMaximumWidth(380)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(12)

        left_hdr_box = QHBoxLayout()
        left_hdr = QLabel("<b>Registered People</b>")
        left_hdr.setStyleSheet("font-size: 14px; color: #ffffff;")
        self.lbl_profile_count = QLabel("0 Profiles")
        self.lbl_profile_count.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        left_hdr_box.addWidget(left_hdr)
        left_hdr_box.addStretch()
        left_hdr_box.addWidget(self.lbl_profile_count)
        left_layout.addLayout(left_hdr_box)

        # Search Filter Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search people...")
        self.txt_search.textChanged.connect(self._filter_profiles)
        left_layout.addWidget(self.txt_search)

        self.list_widget = QListWidget()
        self.list_widget.setCursor(Qt.PointingHandCursor)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; padding: 4px; outline: 0px; }"
            "QListWidget::item { border-bottom: 1px solid #1e293b; border-radius: 8px; margin-bottom: 4px; }"
            "QListWidget::item:selected { background-color: #1e293b; border: 1px solid #38bdf8; }"
            "QListWidget::item:hover { background-color: #131d33; }"
        )
        self.list_widget.currentItemChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.list_widget, 1)

        # Quick Add Button at bottom of list
        btn_quick_add = QPushButton("➕ New Person")
        btn_quick_add.setProperty("class", "SecondaryButton")
        btn_quick_add.setCursor(Qt.PointingHandCursor)
        btn_quick_add.setFixedHeight(34)
        btn_quick_add.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; font-size: 12px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_quick_add.clicked.connect(self._create_profile)
        left_layout.addWidget(btn_quick_add)

        splitter.addWidget(left_widget)

        # Right Column: Selected Profile Studio
        self.detail_card = QFrame()
        self.detail_card.setProperty("class", "Card")
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(14)

        # Profile Hero Header Banner (Elegantly structured card with rounded-square styling)
        self.hero_banner = QFrame()
        self.hero_banner.setStyleSheet(
            "background-color: #0c1322; border: 1px solid #1e293b; border-radius: 14px; padding: 14px 16px;"
        )
        hero_layout = QVBoxLayout(self.hero_banner)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(12)

        # Row 1: Profile Identity (Edge-to-Edge Rounded-Square Avatar + Name + Status Pills) & Primary Action
        identity_row = QHBoxLayout()
        identity_row.setSpacing(16)
        identity_row.setAlignment(Qt.AlignVCenter)

        # Modern Edge-to-Edge Rounded-Square Avatar (92x92)
        self.hero_avatar = ImageCoverWidget(None, width=92, height=92, radius=12)
        self.hero_avatar.setStyleSheet("border: 2px solid #38bdf8; border-radius: 12px;")
        identity_row.addWidget(self.hero_avatar)

        # Name & Status Pills Column
        name_pills_col = QVBoxLayout()
        name_pills_col.setSpacing(6)
        name_pills_col.setAlignment(Qt.AlignVCenter)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.setAlignment(Qt.AlignVCenter)

        self.lbl_profile_name = QLabel("Select a Person")
        self.lbl_profile_name.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff; background: transparent; border: none;")
        name_row.addWidget(self.lbl_profile_name)

        btn_rename_quick = QPushButton("✏️ Rename")
        btn_rename_quick.setCursor(Qt.PointingHandCursor)
        btn_rename_quick.setToolTip("Rename Profile")
        btn_rename_quick.setStyleSheet(
            "QPushButton { background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; font-size: 11px; font-weight: 600; color: #94a3b8; padding: 3px 8px; }"
            "QPushButton:hover { background-color: #334155; color: #ffffff; }"
        )
        btn_rename_quick.clicked.connect(self._rename_profile)
        name_row.addWidget(btn_rename_quick)
        name_row.addStretch()
        name_pills_col.addLayout(name_row)

        # Status Pills Row (Compact, sleek badges)
        self.pills_layout = QHBoxLayout()
        self.pills_layout.setSpacing(6)

        self.pill_embeddings = QLabel("🧠 0 Vectors")
        self.pill_embeddings.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid #334155;"
        )

        self.pill_quality = QLabel("⭐ 5.0")
        self.pill_quality.setStyleSheet(
            "background-color: #1e293b; color: #34d399; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid #334155;"
        )

        self.pill_type = QLabel("👤 Individual")
        self.pill_type.setStyleSheet(
            "background-color: #1e293b; color: #a78bfa; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid #334155;"
        )

        self.pills_layout.addWidget(self.pill_embeddings)
        self.pills_layout.addWidget(self.pill_quality)
        self.pills_layout.addWidget(self.pill_type)
        self.pills_layout.addStretch()
        name_pills_col.addLayout(self.pills_layout)

        identity_row.addLayout(name_pills_col, 1)

        # Prominent Primary Add Reference Photo Button on Right (40px height)
        self.btn_add_ref = QPushButton("➕ Add Reference Photo")
        self.btn_add_ref.setProperty("class", "PrimaryButton")
        self.btn_add_ref.setCursor(Qt.PointingHandCursor)
        self.btn_add_ref.setFixedHeight(40)
        self.btn_add_ref.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 20px; font-size: 13px; border: 1px solid #059669; min-height: 40px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_add_ref.clicked.connect(self._add_reference_photo)
        identity_row.addWidget(self.btn_add_ref, 0, Qt.AlignVCenter)

        hero_layout.addLayout(identity_row)

        # Subtle Separator Line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #1e293b; max-height: 1px; border: none;")
        hero_layout.addWidget(sep)

        # Row 2: Secondary Tools Toolbar (Compact, uniform 30px height, perfect alignment)
        tools_row = QHBoxLayout()
        tools_row.setSpacing(8)
        tools_row.setAlignment(Qt.AlignVCenter)

        self.btn_batch_train = QPushButton("📁 Batch Train")
        self.btn_batch_train.setProperty("class", "SecondaryButton")
        self.btn_batch_train.setCursor(Qt.PointingHandCursor)
        self.btn_batch_train.setFixedHeight(30)
        self.btn_batch_train.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; padding: 0 10px; font-size: 11px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_batch_train.clicked.connect(self._batch_train_profile)
        tools_row.addWidget(self.btn_batch_train)

        self.btn_clean_outliers = QPushButton("🧹 Clean Outliers")
        self.btn_clean_outliers.setProperty("class", "SecondaryButton")
        self.btn_clean_outliers.setCursor(Qt.PointingHandCursor)
        self.btn_clean_outliers.setFixedHeight(30)
        self.btn_clean_outliers.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; padding: 0 10px; font-size: 11px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_clean_outliers.setToolTip("Scan and purge outlier photos or low-star faces.")
        self.btn_clean_outliers.clicked.connect(self._clean_outliers)
        tools_row.addWidget(self.btn_clean_outliers)

        self.btn_group_type = QPushButton("⚙️ Settings")
        self.btn_group_type.setProperty("class", "SecondaryButton")
        self.btn_group_type.setCursor(Qt.PointingHandCursor)
        self.btn_group_type.setFixedHeight(30)
        self.btn_group_type.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; font-weight: 600; border-radius: 6px; padding: 0 10px; font-size: 11px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_group_type.clicked.connect(self._edit_group_settings)
        tools_row.addWidget(self.btn_group_type)

        tools_row.addStretch()

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setProperty("class", "DangerButton")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setFixedHeight(30)
        self.btn_delete.setStyleSheet(
            "QPushButton { background-color: #991b1b; color: #ffffff; font-weight: 600; border-radius: 6px; padding: 0 12px; font-size: 11px; border: 1px solid #dc2626; }"
            "QPushButton:hover { background-color: #dc2626; }"
        )
        self.btn_delete.clicked.connect(self._delete_profile)
        tools_row.addWidget(self.btn_delete)

        hero_layout.addLayout(tools_row)
        detail_layout.addWidget(self.hero_banner)

        # Biometric Recommendation Banner
        self.recommendation_box = QFrame()
        self.recommendation_box.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 8px 12px;"
        )
        rec_layout = QHBoxLayout(self.recommendation_box)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_recommendation = QLabel("✅ Ready for AI Scanning")
        self.lbl_recommendation.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        rec_layout.addWidget(self.lbl_recommendation)
        detail_layout.addWidget(self.recommendation_box)

        # Reference Photos Section Header with Multi-Select Controls
        ref_hdr_box = QHBoxLayout()
        ref_hdr_box.setSpacing(10)
        ref_hdr_box.setAlignment(Qt.AlignVCenter)

        self.lbl_ref_section = QLabel("<b>Enrolled Reference Photos</b>")
        self.lbl_ref_section.setStyleSheet("color: #ffffff; font-size: 13px;")
        ref_hdr_box.addWidget(self.lbl_ref_section)

        ref_hdr_box.addStretch()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.setFixedHeight(26)
        self.btn_select_all.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; padding: 0 10px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background-color: #334155; color: #ffffff; }"
        )
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        ref_hdr_box.addWidget(self.btn_select_all)

        self.btn_batch_delete = QPushButton("🗑️ Delete (0)")
        self.btn_batch_delete.setCursor(Qt.PointingHandCursor)
        self.btn_batch_delete.setFixedHeight(26)
        self.btn_batch_delete.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 4px; padding: 0 12px; font-size: 11px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
            "QPushButton:disabled { background-color: #1e293b; color: #64748b; border: 1px solid #334155; }"
        )
        self.btn_batch_delete.setEnabled(False)
        self.btn_batch_delete.clicked.connect(self._delete_selected_references)
        ref_hdr_box.addWidget(self.btn_batch_delete)

        detail_layout.addLayout(ref_hdr_box)

        # Reference Photos Scroll Area (Responsive 2D Grid)
        self.ref_scroll = QScrollArea()
        self.ref_scroll.setWidgetResizable(True)
        self.ref_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.grid_widget = ResponsiveReferenceGrid()
        self.ref_scroll.setWidget(self.grid_widget)
        detail_layout.addWidget(self.ref_scroll, 1)

        splitter.addWidget(self.detail_card)
        splitter.setSizes([300, 750])

        root_layout.addWidget(splitter, 1)
        self.refresh()

    def _filter_profiles(self, query: str):
        """Filter profile list items based on search text."""
        q = query.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if isinstance(w, ProfileListItemWidget):
                item.setHidden(q not in w.profile_name.lower())
            else:
                item.setHidden(q not in item.text().lower())

    def refresh(self, select_profile_id: str | None = None):
        """Reload profile list from disk while preserving active selection."""
        target_id = select_profile_id or self.current_profile_id
        self.selected_ref_ids.clear()
        self._update_batch_delete_button()

        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        profiles = self.profile_service.list_profiles()
        self.lbl_profile_count.setText(f"{len(profiles)} Profile{'s' if len(profiles) != 1 else ''}")
        selected_item = None

        colors = ["#2563eb", "#059669", "#7c3aed", "#d97706", "#0891b2", "#dc2626"]

        for idx, p in enumerate(profiles):
            refs = p.get("references", [])
            ref_count = len(refs)
            is_group = bool(p.get("is_group_profile"))
            first_ref_path = refs[0].get("stored_path") if refs else None

            item = QListWidgetItem()
            item.setData(Qt.UserRole, p["id"])
            item.setSizeHint(QSize(260, 62))
            self.list_widget.addItem(item)

            bg = colors[idx % len(colors)]
            item_widget = ProfileListItemWidget(
                name=p.get("name", "Unknown"),
                ref_count=ref_count,
                avatar_path=first_ref_path,
                is_group=is_group,
                bg_color=bg,
            )
            self.list_widget.setItemWidget(item, item_widget)

            if target_id and p["id"] == target_id:
                selected_item = item

        self.list_widget.blockSignals(False)

        if selected_item:
            self.list_widget.setCurrentItem(selected_item)
            self._load_profile_details(selected_item.data(Qt.UserRole))
        elif self.list_widget.count() > 0:
            first_item = self.list_widget.item(0)
            self.list_widget.setCurrentItem(first_item)
            self._load_profile_details(first_item.data(Qt.UserRole))
        else:
            self.current_profile_id = None
            self.lbl_profile_name.setText("No Profiles Registered")
            self.hero_avatar.set_initials("?", bg_color="#475569")
            self.pill_embeddings.setText("🧠 0 Vectors")
            self.pill_quality.setText("⭐ 0.0")
            self.pill_type.setText("👤 None")
            self.lbl_recommendation.setText("👋 Click '➕ Create Profile' above to enroll your first person.")
            self.grid_widget.clear()

    def _on_profile_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if current:
            p_id = current.data(Qt.UserRole)
            self._load_profile_details(p_id)

    def _load_profile_details(self, profile_id: str):
        self.current_profile_id = profile_id
        self.selected_ref_ids.clear()
        self._update_batch_delete_button()

        profile = self.profile_service.get_profile(profile_id)
        if not profile:
            return

        p_name = profile.get("name", "Unknown")
        refs = profile.get("references", [])
        embs = profile.get("embeddings", [])
        is_group = bool(profile.get("is_group_profile"))

        # Update Hero Banner
        group_tag = " [Group]" if is_group else ""
        self.lbl_profile_name.setText(f"{p_name}{group_tag}")

        # Update Edge-to-Edge Avatar (92x92 with zero black borders)
        if refs:
            first_ref = refs[0].get("stored_path")
            if first_ref and Path(first_ref).exists():
                self.hero_avatar.set_image_path(str(first_ref))
            else:
                self.hero_avatar.set_initials(p_name, bg_color="#2563eb")
        else:
            self.hero_avatar.set_initials(p_name, bg_color="#2563eb")

        # Update Pills (Compact)
        self.pill_embeddings.setText(f"🧠 {len(embs)} Vectors")
        self.pill_type.setText("👥 Group" if is_group else "👤 Individual")

        # Compute Quality Score
        if refs:
            stars = [r.get("quality_stars", 5) if "quality_stars" in r else r.get("quality", {}).get("stars", 5) for r in refs]
            avg_stars = sum(stars) / len(stars) if stars else 5.0
            self.pill_quality.setText(f"⭐ {avg_stars:.1f}")
        else:
            self.pill_quality.setText("⭐ No Refs")

        # Recommendation Text
        if len(refs) == 0:
            self.lbl_recommendation.setText("⚠️ <b>No reference photos yet:</b> Add at least 1 clear face photo for AI recognition.")
            self.lbl_recommendation.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: 600;")
        elif len(refs) < 3:
            self.lbl_recommendation.setText("💡 <b>Good:</b> Adding 2+ more multi-angle photos boosts matching accuracy to 99.86%.")
            self.lbl_recommendation.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_recommendation.setText("✅ <b>Excellent Biometric Coverage:</b> Ready for high-precision recognition across varied lighting and angles.")
            self.lbl_recommendation.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 600;")

        self._display_references(profile)

    def _display_references(self, profile: dict[str, Any]):
        references = profile.get("references", [])
        self.lbl_ref_section.setText(f"<b>Enrolled Reference Photos ({len(references)})</b>")

        cards: list[QWidget] = []

        # 1. Add Photo Action Tile (Fluid expanding width)
        add_tile = QFrame()
        add_tile.setProperty("class", "ActionTileCard")
        add_tile.setCursor(Qt.PointingHandCursor)
        add_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_tile.setMinimumWidth(130)
        add_tile.setMaximumWidth(260)
        add_tile.setFixedHeight(198)
        at_layout = QVBoxLayout(add_tile)
        at_layout.setContentsMargins(8, 12, 8, 12)
        at_layout.setSpacing(6)
        at_layout.setAlignment(Qt.AlignCenter)

        at_icon = QLabel("📷")
        at_icon.setStyleSheet("font-size: 26px; background: transparent; border: none;")
        at_icon.setAlignment(Qt.AlignCenter)
        at_icon.setCursor(Qt.PointingHandCursor)

        at_lbl = QLabel("Add Photo")
        at_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8; background: transparent; border: none;")
        at_lbl.setAlignment(Qt.AlignCenter)
        at_lbl.setCursor(Qt.PointingHandCursor)

        at_sub = QLabel("Upload Face")
        at_sub.setStyleSheet("font-size: 11px; color: #64748b; background: transparent; border: none;")
        at_sub.setAlignment(Qt.AlignCenter)
        at_sub.setCursor(Qt.PointingHandCursor)

        at_layout.addWidget(at_icon)
        at_layout.addWidget(at_lbl)
        at_layout.addWidget(at_sub)
        add_tile.mousePressEvent = lambda _: self._add_reference_photo()
        cards.append(add_tile)

        # 2. Batch Train Action Tile (Fluid expanding width)
        batch_tile = QFrame()
        batch_tile.setProperty("class", "ActionTileCard")
        batch_tile.setCursor(Qt.PointingHandCursor)
        batch_tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        batch_tile.setMinimumWidth(130)
        batch_tile.setMaximumWidth(260)
        batch_tile.setFixedHeight(198)
        bt_layout = QVBoxLayout(batch_tile)
        bt_layout.setContentsMargins(8, 12, 8, 12)
        bt_layout.setSpacing(6)
        bt_layout.setAlignment(Qt.AlignCenter)

        bt_icon = QLabel("📁")
        bt_icon.setStyleSheet("font-size: 26px; background: transparent; border: none;")
        bt_icon.setAlignment(Qt.AlignCenter)
        bt_icon.setCursor(Qt.PointingHandCursor)

        bt_lbl = QLabel("Batch Train")
        bt_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #a78bfa; background: transparent; border: none;")
        bt_lbl.setAlignment(Qt.AlignCenter)
        bt_lbl.setCursor(Qt.PointingHandCursor)

        bt_sub = QLabel("Import Folder")
        bt_sub.setStyleSheet("font-size: 11px; color: #64748b; background: transparent; border: none;")
        bt_sub.setAlignment(Qt.AlignCenter)
        bt_sub.setCursor(Qt.PointingHandCursor)

        bt_layout.addWidget(bt_icon)
        bt_layout.addWidget(bt_lbl)
        bt_layout.addWidget(bt_sub)
        batch_tile.mousePressEvent = lambda _: self._batch_train_profile()
        cards.append(batch_tile)

        # 3. Interactive Reference Photo Cards with Edge-to-Edge Photo Covers (Zero Black Bars)
        for ref in references:
            ref_id = ref.get("id")
            card = ReferencePhotoCard(
                ref=ref,
                is_selected=(ref_id in self.selected_ref_ids),
                on_toggle=self._on_ref_toggled,
                on_delete=self._remove_reference,
            )
            cards.append(card)

        self.grid_widget.set_cards(cards)

    def _on_ref_toggled(self, ref_id: str, is_checked: bool):
        if is_checked:
            self.selected_ref_ids.add(ref_id)
        else:
            self.selected_ref_ids.discard(ref_id)
        self._update_batch_delete_button()

    def _update_batch_delete_button(self):
        count = len(self.selected_ref_ids)
        self.btn_batch_delete.setText(f"🗑️ Delete ({count})")
        self.btn_batch_delete.setEnabled(count > 0)

        # Update Select All text
        if self.current_profile_id:
            profile = self.profile_service.get_profile(self.current_profile_id)
            total_refs = len(profile.get("references", [])) if profile else 0
            if count > 0 and count == total_refs:
                self.btn_select_all.setText("Deselect All")
            else:
                self.btn_select_all.setText("Select All")

    def _toggle_select_all(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        refs = profile.get("references", [])
        total_ids = {r.get("id") for r in refs if r.get("id")}

        if len(self.selected_ref_ids) == len(total_ids):
            self.selected_ref_ids.clear()
        else:
            self.selected_ref_ids = set(total_ids)

        self._display_references(profile)
        self._update_batch_delete_button()

    def _delete_selected_references(self):
        if not self.current_profile_id or not self.selected_ref_ids:
            return

        profile = self.profile_service.get_profile(self.current_profile_id)
        p_name = profile.get("name", "this person") if profile else "this person"
        count = len(self.selected_ref_ids)

        res = QMessageBox.question(
            self,
            "Confirm Batch Deletion",
            f"Are you sure you want to delete {count} selected reference photo{'s' if count != 1 else ''} from '{p_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            ref_ids_to_del = list(self.selected_ref_ids)
            p_id = self.current_profile_id

            prog_dlg = QProgressDialog(f"Removing {count} reference photo(s)...", None, 0, 0, self)
            prog_dlg.setWindowTitle("Deleting Reference Photos")
            prog_dlg.setWindowModality(Qt.WindowModal)
            prog_dlg.setMinimumDuration(0)
            prog_dlg.setValue(0)
            prog_dlg.setCancelButton(None)
            prog_dlg.setStyleSheet(
                "QProgressDialog { background-color: #0f172a; color: #ffffff; }"
                "QLabel { color: #ffffff; font-size: 12px; }"
                "QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: #ffffff; background: #0b0f19; }"
                "QProgressBar::chunk { background-color: #ef4444; border-radius: 5px; }"
            )

            worker = ProfileDeleteRefsWorker(self.profile_service, p_id, ref_ids_to_del)

            def on_finished(removed: int, err_msg: str):
                prog_dlg.close()
                self.selected_ref_ids.clear()
                self.refresh(select_profile_id=p_id)
                if err_msg:
                    QMessageBox.warning(self, "Deletion Error", f"Encountered an issue: {err_msg}")
                else:
                    QMessageBox.information(self, "Photos Deleted", f"Successfully removed {removed} reference photo(s).")

            worker.finished_signal.connect(on_finished)
            worker.start()
            self._del_refs_worker = worker

    def _remove_reference(self, ref_id: str):
        if self.current_profile_id and ref_id:
            res = QMessageBox.question(
                self,
                "Confirm Remove",
                "Are you sure you want to remove this reference photo?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if res == QMessageBox.Yes:
                self.profile_service.remove_reference_photo(self.current_profile_id, ref_id)
                self.selected_ref_ids.discard(ref_id)
                self.refresh(select_profile_id=self.current_profile_id)

    def _create_profile(self):
        dlg = CreateProfileDialog(self, self.profile_service.list_profiles())
        if dlg.exec() == CreateProfileDialog.Accepted:
            name = dlg.profile_name
            is_group = dlg.is_group_profile
            compulsory_ids = dlg.selected_compulsory_ids

            if name:
                try:
                    new_p = self.profile_service.create_profile(
                        name=name,
                        is_group_profile=is_group,
                        compulsory_profile_ids=compulsory_ids,
                    )
                    self.refresh(select_profile_id=new_p["id"])
                except ValueError as ve:
                    QMessageBox.warning(self, "Profile Creation Error", str(ve))

    def _edit_group_settings(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        all_profiles = [p for p in self.profile_service.list_profiles() if p["id"] != self.current_profile_id]
        dlg = CreateProfileDialog(self, all_profiles, initial_profile=profile)
        if dlg.exec() == CreateProfileDialog.Accepted:
            self.profile_service.update_profile_type(
                self.current_profile_id,
                is_group_profile=dlg.is_group_profile,
                compulsory_profile_ids=dlg.selected_compulsory_ids,
            )
            if dlg.profile_name != profile["name"]:
                try:
                    self.profile_service.rename_profile(self.current_profile_id, dlg.profile_name)
                except ValueError as ve:
                    QMessageBox.warning(self, "Rename Error", str(ve))
            self.refresh(select_profile_id=self.current_profile_id)

    def _rename_profile(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        new_name, ok = QInputDialog.getText(
            self, "Rename Profile", "Enter New Profile Name:", text=profile["name"]
        )
        if ok and new_name.strip():
            try:
                self.profile_service.rename_profile(self.current_profile_id, new_name.strip())
                self.refresh(select_profile_id=self.current_profile_id)
            except ValueError as ve:
                QMessageBox.warning(self, "Rename Error", str(ve))

    def _delete_profile(self):
        if not self.current_profile_id:
            return
        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        res = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete profile '{profile['name']}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.profile_service.delete_profile(self.current_profile_id)
            self.current_profile_id = None
            self.refresh()

    def _add_reference_photo(self):
        if not self.current_profile_id:
            QMessageBox.warning(self, "No Profile Selected", "Please select or create a profile first.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Photo",
            "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.heic *.tiff *.cr2 *.nef *.arw *.dng);;All Files (*)",
        )
        if not file_path:
            return

        p_path = Path(file_path)
        _, locations, crops = self.profile_service.detect_faces_in_reference(p_path)

        selected_idx = 0
        if len(locations) > 1:
            dlg = FaceSelectorDialog(self, crops)
            if dlg.exec() == FaceSelectorDialog.Accepted:
                selected_idx = dlg.selected_index
            else:
                return

        success, msg = self.profile_service.add_reference_photo(
            self.current_profile_id, p_path, selected_face_index=selected_idx, use_fallback_if_no_face=True
        )
        if success:
            QMessageBox.information(self, "Success", "Reference photo added successfully.")
            self.refresh(select_profile_id=self.current_profile_id)
        else:
            QMessageBox.warning(self, "Error", f"Failed to add reference photo: {msg}")

    def _open_live_face_scanner(self, profile_id: str | None = None):
        """Open interactive 360° live webcam face scanner dialog."""
        engine = self.face_engine or getattr(self.profile_service, "face_engine", None)
        if not engine:
            QMessageBox.warning(self, "Engine Not Available", "Face recognition engine is not initialized.")
            return

        dlg = LiveFaceScannerDialog(
            parent=self,
            profile_service=self.profile_service,
            face_engine=engine,
            target_profile_id=profile_id,
        )
        if dlg.exec() == QDialog.Accepted:
            selected_id = profile_id or dlg.created_profile_id
            self.refresh(select_profile_id=selected_id)

    def _batch_train_profile(self):
        if not self.current_profile_id:
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Photos of Person")
        if not folder:
            return

        profile = self.profile_service.get_profile(self.current_profile_id)
        p_name = profile.get("name", "Person") if profile else "Person"

        self.btn_batch_train.setEnabled(False)
        self.btn_batch_train.setText("⏳ Training...")

        self.worker = ProfileBatchTrainWorker(
            profile_service=self.profile_service,
            profile_id=self.current_profile_id,
            folder_path=Path(folder),
        )
        self.worker.finished_signal.connect(
            lambda added, total, msg, p_id=self.current_profile_id, name=p_name: self._on_batch_train_finished(added, total, msg, p_id, name)
        )
        self.worker.start()

    def _on_batch_train_finished(self, added: int, total: int, msg: str, profile_id: str, profile_name: str):
        self.btn_batch_train.setEnabled(True)
        self.btn_batch_train.setText("📁 Batch Train")

        if added > 0:
            QMessageBox.information(
                self,
                "Batch Training Complete",
                f"✨ Successfully imported {added} facial reference vectors for {profile_name} from {total} photos!\n\nProfile recognition accuracy and context updated.",
            )
        else:
            QMessageBox.warning(self, "No Facial Vectors Added", msg)

        self.refresh(select_profile_id=profile_id)

    def _clean_outliers(self):
        if not self.current_profile_id:
            return

        profile = self.profile_service.get_profile(self.current_profile_id)
        if not profile:
            return

        p_name = profile.get("name", "this person")
        res = QMessageBox.question(
            self,
            "Clean Profile Outliers & Low Quality Photos",
            f"Would you like to scan and clean reference photos in '{p_name}'?\n\n"
            "This will automatically:\n"
            "1. Remove photos belonging to a different person (outliers).\n"
            "2. Remove low-quality / blurry photos (< 4 stars).\n\n"
            "Leaves only 100% verified 4-star and 5-star reference photos for maximum scanning precision.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            p_id = self.current_profile_id

            prog_dlg = QProgressDialog(f"Analyzing facial vectors and cleaning outliers for '{p_name}'...", None, 0, 0, self)
            prog_dlg.setWindowTitle("Cleaning Profile Outliers")
            prog_dlg.setWindowModality(Qt.WindowModal)
            prog_dlg.setMinimumDuration(0)
            prog_dlg.setValue(0)
            prog_dlg.setCancelButton(None)
            prog_dlg.setStyleSheet(
                "QProgressDialog { background-color: #0f172a; color: #ffffff; }"
                "QLabel { color: #ffffff; font-size: 12px; }"
                "QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: #ffffff; background: #0b0f19; }"
                "QProgressBar::chunk { background-color: #10b981; border-radius: 5px; }"
            )

            worker = ProfileCleanOutliersWorker(self.profile_service, p_id, min_similarity=60.0, min_stars=4)

            def on_finished(removed: int, remaining: int, err_msg: str):
                prog_dlg.close()
                self.refresh(select_profile_id=p_id)
                if err_msg:
                    QMessageBox.warning(self, "Cleaning Error", f"Encountered an issue: {err_msg}")
                elif removed > 0:
                    QMessageBox.information(
                        self,
                        "Profile Cleaned",
                        f"🧹 Successfully purged {removed} outlier / low-star photos from {p_name}.\n\n"
                        f"⭐ {remaining} high-quality (4 & 5-star) reference photos remain for high-precision recognition.",
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Profile Clean",
                        f"✅ All {remaining} reference photos are verified 4/5-star matches for {p_name}!",
                    )

            worker.finished_signal.connect(on_finished)
            worker.start()
            self._clean_worker = worker


class ProfileCleanOutliersWorker(QThread):
    finished_signal = Signal(int, int, str)

    def __init__(self, profile_service: ProfileService, profile_id: str, min_similarity: float = 60.0, min_stars: int = 4):
        super().__init__()
        self.profile_service = profile_service
        self.profile_id = profile_id
        self.min_similarity = min_similarity
        self.min_stars = min_stars

    def run(self):
        try:
            removed, remaining = self.profile_service.prune_profile_outliers(
                self.profile_id, min_similarity=self.min_similarity, min_stars=self.min_stars
            )
            self.finished_signal.emit(removed, remaining, "")
        except Exception as e:
            self.finished_signal.emit(0, 0, str(e))


class ProfileDeleteRefsWorker(QThread):
    finished_signal = Signal(int, str)

    def __init__(self, profile_service: ProfileService, profile_id: str, ref_ids: list[str]):
        super().__init__()
        self.profile_service = profile_service
        self.profile_id = profile_id
        self.ref_ids = ref_ids

    def run(self):
        try:
            removed = self.profile_service.remove_reference_photos(self.profile_id, self.ref_ids)
            self.finished_signal.emit(removed, "")
        except Exception as e:
            self.finished_signal.emit(0, str(e))


class ProfileBatchTrainWorker(QThread):
    finished_signal = Signal(int, int, str)

    def __init__(self, profile_service: ProfileService, profile_id: str, folder_path: Path):
        super().__init__()
        self.profile_service = profile_service
        self.profile_id = profile_id
        self.folder_path = folder_path

    def run(self):
        try:
            added, total, msg = self.profile_service.batch_add_reference_photos_from_folder(
                self.profile_id, self.folder_path
            )
            self.finished_signal.emit(added, total, msg)
        except Exception as e:
            self.finished_signal.emit(0, 0, str(e))


class CreateProfileDialog(QDialog):
    """Dialog for creating or editing Individual or Group profiles with smooth scrolling and fixed actions."""

    def __init__(
        self,
        parent: QWidget | None,
        existing_profiles: list[dict[str, Any]],
        initial_profile: dict[str, Any] | None = None,
    ):
        super().__init__(parent)
        self.initial_profile = initial_profile
        self.setWindowTitle("⚙️ Edit Profile Settings" if initial_profile else "👤 Create New Profile")
        self.setMinimumSize(480, 480)
        self.resize(500, 560)
        self.existing_profiles = existing_profiles

        self.profile_name: str = initial_profile.get("name", "") if initial_profile else ""
        self.is_group_profile: bool = initial_profile.get("is_group_profile", False) if initial_profile else False
        self.selected_compulsory_ids: list[str] = (
            initial_profile.get("compulsory_profile_ids", []) if initial_profile else []
        )

        self._setup_ui()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(14)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        lbl_title = QLabel("⚙️ Profile Settings" if self.initial_profile else "👤 Create Profile")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        lbl_sub = QLabel(
            "Configure person identity or group detection settings."
            if not self.initial_profile
            else "Update profile name and compulsory group members."
        )
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        root_layout.addLayout(title_box)

        # Middle Form Content Area
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setStyleSheet("background: transparent; border: none;")

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(14)

        # 1. Profile Name
        name_card = QFrame()
        name_card.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        nc_layout = QVBoxLayout(name_card)
        nc_layout.setSpacing(6)

        lbl_name_tag = QLabel("<b>Profile Name:</b>")
        lbl_name_tag.setStyleSheet("color: #ffffff; font-size: 13px;")
        nc_layout.addWidget(lbl_name_tag)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g. Harsh, Mom, Dad, or Couple: Alex & Sam")
        if self.profile_name:
            self.txt_name.setText(self.profile_name)
        nc_layout.addWidget(self.txt_name)
        form_layout.addWidget(name_card)

        # 2. Profile Type
        type_card = QFrame()
        type_card.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        tc_layout = QVBoxLayout(type_card)
        tc_layout.setSpacing(10)

        lbl_type_tag = QLabel("<b>Profile Type:</b>")
        lbl_type_tag.setStyleSheet("color: #ffffff; font-size: 13px;")
        tc_layout.addWidget(lbl_type_tag)

        self.radio_indiv = QRadioButton("👤 Individual Person Profile (Standard)")
        self.radio_indiv.setStyleSheet("color: #ffffff; font-weight: 600;")
        self.radio_indiv.setCursor(Qt.PointingHandCursor)

        self.radio_group = QRadioButton("👥 Group Profile (Requires ALL compulsory members in photo)")
        self.radio_group.setStyleSheet("color: #ffffff; font-weight: 600;")
        self.radio_group.setCursor(Qt.PointingHandCursor)

        if self.is_group_profile:
            self.radio_group.setChecked(True)
        else:
            self.radio_indiv.setChecked(True)

        self.btn_grp = QButtonGroup(self)
        self.btn_grp.addButton(self.radio_indiv, 0)
        self.btn_grp.addButton(self.radio_group, 1)

        tc_layout.addWidget(self.radio_indiv)
        tc_layout.addWidget(self.radio_group)
        form_layout.addWidget(type_card)

        # 3. Compulsory Profiles Selection Box
        self.compulsory_frame = QFrame()
        self.compulsory_frame.setStyleSheet("background-color: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 12px;")
        cf_layout = QVBoxLayout(self.compulsory_frame)
        cf_layout.setSpacing(8)

        self.lbl_compulsory_header = QLabel("<b>Select Compulsory People for this Group:</b>")
        self.lbl_compulsory_header.setStyleSheet("color: #38bdf8; font-size: 13px;")
        cf_layout.addWidget(self.lbl_compulsory_header)

        # Search filter for people list
        self.txt_filter_people = QLineEdit()
        self.txt_filter_people.setPlaceholderText("🔍 Filter people...")
        self.txt_filter_people.textChanged.connect(self._filter_compulsory_people)
        cf_layout.addWidget(self.txt_filter_people)

        # Scrollable ListWidget for Checkboxes
        self.compulsory_list = QListWidget()
        self.compulsory_list.setCursor(Qt.PointingHandCursor)
        self.compulsory_list.setStyleSheet(
            "QListWidget { background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; color: #f8fafc; padding: 4px; }"
            "QListWidget::item { padding: 8px 10px; border-bottom: 1px solid #1e293b; }"
            "QListWidget::item:hover { background-color: #1e293b; }"
        )
        self.compulsory_list.setFixedHeight(180)

        for p in self.existing_profiles:
            if not p.get("is_group_profile"):
                item = QListWidgetItem(f"👤  {p.get('name', 'Unknown')}")
                item.setData(Qt.UserRole, p.get("id"))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if p.get("id") in self.selected_compulsory_ids:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.compulsory_list.addItem(item)

        cf_layout.addWidget(self.compulsory_list)
        form_layout.addWidget(self.compulsory_frame)

        self.compulsory_frame.setVisible(self.is_group_profile)
        self.radio_group.toggled.connect(self.compulsory_frame.setVisible)

        form_layout.addStretch()
        form_scroll.setWidget(form_widget)
        root_layout.addWidget(form_scroll, 1)

        # Fixed Footer Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("class", "SecondaryButton")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()

        if not self.initial_profile:
            btn_scan_cam = QPushButton("🎥 Scan with Camera")
            btn_scan_cam.setProperty("class", "SecondaryButton")
            btn_scan_cam.setCursor(Qt.PointingHandCursor)
            btn_scan_cam.setFixedHeight(38)
            btn_scan_cam.setStyleSheet("background-color: #1e3a8a; border: 1px solid #38bdf8; color: #38bdf8; font-weight: bold; padding: 0 16px;")
            btn_scan_cam.setToolTip("Open live camera to capture 5-angle 360° face photos for this person.")
            btn_scan_cam.clicked.connect(self._on_scan_with_camera)
            btn_layout.addWidget(btn_scan_cam)

        btn_text = "💾 Save Changes" if self.initial_profile else "👤 Create Profile"
        self.btn_ok = QPushButton(btn_text)
        self.btn_ok.setProperty("class", "PrimaryButton")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setFixedHeight(38)
        self.btn_ok.setStyleSheet("background-color: #10b981; color: #ffffff; font-weight: bold; padding: 0 20px;")
        self.btn_ok.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.btn_ok)

        root_layout.addLayout(btn_layout)

    def _filter_compulsory_people(self, query: str):
        q = query.strip().lower()
        for i in range(self.compulsory_list.count()):
            item = self.compulsory_list.item(i)
            item.setHidden(q not in item.text().lower())

    def _on_confirm(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a profile name.")
            return

        self.profile_name = name
        self.is_group_profile = self.radio_group.isChecked()

        if self.is_group_profile:
            selected_ids = []
            for i in range(self.compulsory_list.count()):
                item = self.compulsory_list.item(i)
                if item.checkState() == Qt.Checked:
                    selected_ids.append(item.data(Qt.UserRole))
            self.selected_compulsory_ids = selected_ids

            if len(self.selected_compulsory_ids) < 2:
                QMessageBox.warning(
                    self,
                    "Group Profile Setup",
                    "Please select at least 2 compulsory individual profiles for a Group Profile.",
                )
                return

        self.accept()

    def _on_scan_with_camera(self):
        parent = self.parent()
        self.reject()
        if parent and hasattr(parent, "_open_live_face_scanner"):
            parent._open_live_face_scanner()
