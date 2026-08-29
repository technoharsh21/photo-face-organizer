"""
UI Stylesheet & Design System Module for PySide6.

Provides a clean, modern, high-contrast dark slate desktop theme for Photo Face Organizer.
Follows 8px spacing system, strong typography hierarchy, and polished component variants.
"""

STYLESHEET = """
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
    background-color: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 12px;
    padding: 16px;
}

QFrame[class="Card"]:hover, QFrame.Card:hover {
    border-color: #3b82f6 !important;
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
    background-color: #111827;
    border: 2px solid #38bdf8;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
    selection-background-color: #0284c7;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border: 2px solid #60a5fa;
    background-color: #1e293b;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #93c5fd;
    background-color: #1e293b;
    color: #ffffff;
}

/* High-Contrast Dropdowns (QComboBox) */
QComboBox {
    background-color: #111827;
    border: 2px solid #38bdf8;
    border-radius: 8px;
    padding: 8px 38px 8px 14px;
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
    min-height: 24px;
}

QComboBox:hover {
    border: 2px solid #60a5fa;
    background-color: #1e293b;
}

QComboBox:focus {
    border: 2px solid #93c5fd;
    background-color: #1e293b;
    color: #ffffff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 34px;
    border-left: 2px solid #38bdf8;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #0284c7;
}

QComboBox::drop-down:hover {
    background-color: #0369a1;
}

QComboBox::down-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'></polyline></svg>");
    width: 13px;
    height: 13px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #ffffff;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    border: 2px solid #38bdf8;
    border-radius: 8px;
    outline: 0px;
    padding: 6px;
}

QComboBox QAbstractItemView::item {
    background-color: #0f172a;
    color: #ffffff;
    min-height: 32px;
    padding: 6px 14px;
    border-radius: 4px;
    margin: 2px 0;
}

QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: bold;
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
