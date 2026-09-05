"""
UI Stylesheet & Design System Module for PySide6.

Provides a clean, modern, high-contrast dark slate desktop theme for Photo Face Organizer.
Follows 8px spacing system, strong typography hierarchy, and polished component variants.
"""

import os as _os
from PySide6.QtGui import QColor, QPalette

_ASSETS_DIR = _os.path.join(_os.path.dirname(__file__), "assets")
_ARROW_SVG = _os.path.join(_ASSETS_DIR, "arrow_down.svg").replace("\\", "/")


def get_stylesheet() -> str:
    """Return the full application stylesheet with correct asset paths resolved."""
    return _STYLESHEET_TEMPLATE.replace("__ARROW_SVG__", _ARROW_SVG)


def get_dark_palette() -> QPalette:
    """Return a QPalette matching the dark theme.

    Palette-driven internals (scroll-area viewports, item views inside file
    dialogs, completer popups) ignore QSS and fall back to the OS system
    palette, which renders white on a light-themed Windows desktop.
    """
    palette = QPalette()

    window = QColor("#080c14")
    base = QColor("#0f172a")
    alt_base = QColor("#162238")
    button = QColor("#1e293b")
    text = QColor("#e2e8f0")
    heading = QColor("#f8fafc")
    muted = QColor("#64748b")
    accent = QColor("#0284c7")
    white = QColor("#ffffff")

    background_roles = {
        QPalette.ColorRole.Window: window,
        QPalette.ColorRole.Base: base,
        QPalette.ColorRole.AlternateBase: alt_base,
        QPalette.ColorRole.Button: button,
        QPalette.ColorRole.ToolTipBase: button,
        QPalette.ColorRole.Dark: QColor("#0b0f19"),
        QPalette.ColorRole.Mid: QColor("#334155"),
        QPalette.ColorRole.Light: QColor("#334155"),
        QPalette.ColorRole.Midlight: QColor("#475569"),
    }
    foreground_roles = {
        QPalette.ColorRole.WindowText: heading,
        QPalette.ColorRole.Text: text,
        QPalette.ColorRole.ButtonText: heading,
        QPalette.ColorRole.ToolTipText: white,
        QPalette.ColorRole.PlaceholderText: muted,
        QPalette.ColorRole.BrightText: white,
        QPalette.ColorRole.Link: QColor("#38bdf8"),
        QPalette.ColorRole.Highlight: accent,
        QPalette.ColorRole.HighlightedText: white,
    }

    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        for role, color in {**background_roles, **foreground_roles}.items():
            palette.setColor(group, role, color)

    for role, color in background_roles.items():
        palette.setColor(QPalette.ColorGroup.Disabled, role, color)
    for role, color in foreground_roles.items():
        palette.setColor(
            QPalette.ColorGroup.Disabled,
            role,
            color if role in (QPalette.ColorRole.Highlight, QPalette.ColorRole.HighlightedText) else muted,
        )

    return palette


# Keep STYLESHEET as a module-level alias so existing imports keep working.
# Populated at the bottom of this module after the template is defined.
STYLESHEET = ""  # will be set at bottom of file

_STYLESHEET_TEMPLATE = """
/* =========================================================================
   1. Global Window & Base Controls
   ========================================================================= */
QMainWindow, QDialog, QMessageBox, QInputDialog, QFileDialog {
    background-color: #080c14;
    color: #f8fafc;
    font-family: 'Segoe UI', Roboto, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
}

QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', Roboto, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

/* =========================================================================
   1b. Scroll Areas & Generic Item Views
   Painted explicitly so nothing falls back to the OS system palette
   (white rectangles on light-themed Windows).
   ========================================================================= */
QScrollArea {
    background-color: #080c14;
    border: none;
}

QScrollArea > QWidget {
    background-color: #080c14;
}

QAbstractItemView {
    background-color: #0f172a;
    alternate-background-color: #0f172a;
    color: #e2e8f0;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    border: 1px solid #1e293b;
    outline: 0px;
}

/* =========================================================================
   2. Sidebar Navigation
   ========================================================================= */
QFrame#Sidebar {
    background-color: #0b0f19;
    border-right: 1px solid #1e293b;
    min-width: 235px;
    max-width: 235px;
}

QLabel#AppTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    padding: 16px 16px 4px 16px;
    letter-spacing: 0.5px;
}

QPushButton[class="NavButton"], QPushButton.NavButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 2px 8px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}

QPushButton[class="NavButton"]:hover, QPushButton.NavButton:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

QPushButton[class="NavButton"]:checked, QPushButton.NavButton:checked,
QPushButton[class="NavButton"].active, QPushButton.NavButton.active {
    background-color: #1d4ed8;
    color: #ffffff;
    font-weight: 700;
    border-left: 4px solid #38bdf8;
}

/* =========================================================================
   3. Main Content Area & Cards
   ========================================================================= */
QFrame#ContentFrame {
    background-color: #080c14;
}

/* Elevated Cards & Containers */
QFrame[class="Card"], QFrame.Card {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px;
    padding: 16px;
}

QFrame[class="Card"]:hover, QFrame.Card:hover {
    border-color: #3b82f6 !important;
}

QFrame[class="StatCardBlue"], QFrame.StatCardBlue {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-top: 3px solid #3b82f6 !important;
    border-radius: 12px;
    padding: 16px;
}

QFrame[class="StatCardGreen"], QFrame.StatCardGreen {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-top: 3px solid #10b981 !important;
    border-radius: 12px;
    padding: 16px;
}

QFrame[class="StatCardPurple"], QFrame.StatCardPurple {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-top: 3px solid #8b5cf6 !important;
    border-radius: 12px;
    padding: 16px;
}

QFrame[class="StatCardAmber"], QFrame.StatCardAmber {
    background-color: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-top: 3px solid #f59e0b !important;
    border-radius: 12px;
    padding: 16px;
}

QFrame[class="WorkflowCard"], QFrame.WorkflowCard {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 18px;
}

QFrame[class="WorkflowCard"]:hover, QFrame.WorkflowCard:hover {
    border-color: #3b82f6;
    background-color: #131f38;
}

QFrame[class="ProfileShowcaseCard"], QFrame.ProfileShowcaseCard {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 14px 16px;
}

QFrame[class="ProfileShowcaseCard"]:hover, QFrame.ProfileShowcaseCard:hover {
    border-color: #38bdf8;
    background-color: #131f38;
}

QFrame[class="AddProfileCard"], QFrame.AddProfileCard {
    background-color: #090e1a;
    border: 2px dashed #334155;
    border-radius: 12px;
    padding: 14px 16px;
}

QFrame[class="AddProfileCard"]:hover, QFrame.AddProfileCard:hover {
    border-color: #38bdf8;
    background-color: #131f38;
}

QFrame[class="DiagnosticsCard"], QFrame.DiagnosticsCard {
    background-color: #0b1120;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 14px 18px;
}

QFrame[class="ReferencePhotoCard"], QFrame.ReferencePhotoCard {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 8px;
}

QFrame[class="ReferencePhotoCard"]:hover, QFrame.ReferencePhotoCard:hover {
    border-color: #38bdf8;
    background-color: #131f38;
}

QFrame[class="ActionTileCard"], QFrame.ActionTileCard {
    background-color: #090e1a;
    border: 2px dashed #334155;
    border-radius: 10px;
    padding: 8px;
}

QFrame[class="ActionTileCard"]:hover, QFrame.ActionTileCard:hover {
    border-color: #38bdf8;
    background-color: #131f38;
}

/* Badges */
QLabel[class="BadgeBlue"] {
    background-color: #172554;
    color: #60a5fa;
    border: 1px solid #2563eb;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[class="BadgeGreen"] {
    background-color: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[class="BadgePurple"] {
    background-color: #3b0764;
    color: #c084fc;
    border: 1px solid #7c3aed;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[class="BadgeAmber"] {
    background-color: #451a03;
    color: #fbbf24;
    border: 1px solid #d97706;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[class="BadgeCyan"] {
    background-color: #083344;
    color: #22d3ee;
    border: 1px solid #0891b2;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

/* Typography */
QLabel {
    color: #f1f5f9;
}

QLabel[class="PageHeader"], QLabel.PageHeader {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 4px;
}

QLabel[class="SectionHeader"], QLabel.SectionHeader {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
}

QLabel[class="SubHeader"], QLabel.SubHeader {
    font-size: 15px;
    font-weight: 700;
    color: #38bdf8;
}

QLabel[class="StatValue"], QLabel.StatValue {
    font-size: 28px;
    font-weight: 800;
    color: #38bdf8;
}

QLabel[class="StatLabel"], QLabel.StatLabel {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* =========================================================================
   4. Buttons (Primary, Secondary, Danger, Ghost)
   ========================================================================= */
QPushButton {
    background-color: #1e293b;
    color: #ffffff !important;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b !important;
    border-color: #334155;
}

QPushButton[class="PrimaryButton"], QPushButton.PrimaryButton {
    background-color: #10b981 !important;
    color: #ffffff !important;
    border: 1px solid #059669;
    font-weight: 700;
    font-size: 13px;
}

QPushButton[class="PrimaryButton"]:hover, QPushButton.PrimaryButton:hover {
    background-color: #059669 !important;
    border-color: #047857;
}

QPushButton[class="SecondaryButton"], QPushButton.SecondaryButton {
    background-color: #1e293b !important;
    color: #38bdf8 !important;
    border: 1px solid #3b82f6;
    font-weight: 600;
    font-size: 13px;
}

QPushButton[class="SecondaryButton"]:hover, QPushButton.SecondaryButton:hover {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
}

QPushButton[class="DangerButton"], QPushButton.DangerButton {
    background-color: #dc2626 !important;
    color: #ffffff !important;
    border: 1px solid #b91c1c;
    font-weight: 600;
    font-size: 13px;
}

QPushButton[class="DangerButton"]:hover, QPushButton.DangerButton:hover {
    background-color: #b91c1c !important;
}

/* =========================================================================
   5. Form Inputs & High-Contrast Controls
   ========================================================================= */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    selection-background-color: #0284c7;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #38bdf8;
    background-color: #162238;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #38bdf8;
    background-color: #162238;
    color: #ffffff;
}

/* Modern Clean Dropdowns (QComboBox) */
QComboBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 28px 6px 12px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #38bdf8;
    background-color: #162238;
}

QComboBox:focus {
    border: 1px solid #38bdf8;
    background-color: #162238;
    color: #ffffff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url("__ARROW_SVG__");
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #ffffff;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    outline: 0px;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    background-color: #0f172a;
    color: #ffffff;
    min-height: 28px;
    padding: 4px 10px;
    border-radius: 4px;
    margin: 1px 0;
}

QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: bold;
}

/* Modern Horizontal QSlider */
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #0284c7;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #38bdf8;
    border: 2px solid #ffffff;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #67e8f9;
}

/* =========================================================================
   6. Wizard Step Breadcrumbs
   ========================================================================= */
QFrame[class="StepHeader"], QFrame.StepHeader {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 12px;
}

QLabel[class="StepPill"], QLabel.StepPill {
    background-color: #1e293b;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 6px;
}

QLabel[class="StepPillActive"], QLabel.StepPillActive {
    background-color: #0284c7;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 6px;
    border: 1px solid #38bdf8;
}

/* =========================================================================
   7. Radio Buttons & CheckBoxes
   ========================================================================= */
QRadioButton, QCheckBox {
    color: #f8fafc;
    font-size: 13px;
    spacing: 10px;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #64748b;
    background-color: #0f172a;
}

QCheckBox::indicator {
    border-radius: 4px;
}

QRadioButton::indicator:hover, QCheckBox::indicator:hover {
    border-color: #38bdf8;
    background-color: #1e293b;
}

QRadioButton::indicator:checked {
    border-color: #10b981;
    background-color: #10b981;
}

QCheckBox::indicator:checked {
    border-color: #38bdf8;
    background-color: #38bdf8;
}

/* =========================================================================
   8. Lists, Tables & Tree Views
   ========================================================================= */
QListWidget, QTreeWidget, QTableWidget {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    color: #f8fafc;
    outline: 0px;
    padding: 4px;
}

QListWidget::item, QTreeWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #1e293b;
    border-radius: 6px;
    margin-bottom: 2px;
    color: #f8fafc;
}

QListWidget::item:hover, QTreeWidget::item:hover {
    background-color: #1e293b;
    color: #ffffff;
}

QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 700;
}

QHeaderView::section {
    background-color: #0b0f19;
    color: #94a3b8;
    font-weight: 700;
    font-size: 12px;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #1e293b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* =========================================================================
   9. Progress Bar & Visual Feedback
   ========================================================================= */
QProgressBar {
    border: 1px solid #1e293b;
    border-radius: 8px;
    background-color: #0f172a;
    text-align: center;
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    height: 22px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #10b981);
    border-radius: 7px;
}

/* =========================================================================
   10. ScrollBars & Splitters
   ========================================================================= */
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #080c14;
    border: none;
}

QScrollBar:vertical {
    width: 8px;
}

QScrollBar:horizontal {
    height: 8px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #334155;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
}

QSplitter::handle {
    background-color: #1e293b;
}

QSplitter::handle:hover {
    background-color: #38bdf8;
}

/* =========================================================================
   11. ToolTips
   ========================================================================= */
QToolTip {
    background-color: #1e293b;
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""

# Populate the backwards-compatible alias at import time.
STYLESHEET = get_stylesheet()
