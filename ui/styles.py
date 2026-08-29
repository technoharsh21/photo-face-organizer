"""
UI Stylesheet & Theme Module for PySide6.

Provides a clean, modern, high-contrast dark slate desktop theme for Photo Face Organizer.
"""

STYLESHEET = """
/* Global Window & Base Controls */
QMainWindow, QDialog, QMessageBox, QInputDialog, QFileDialog {
    background-color: #0b0f19;
    color: #f8fafc;
    font-family: 'Segoe UI', Roboto, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
}

QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', Roboto, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #080c14;
    border-right: 1px solid #1e293b;
    min-width: 230px;
    max-width: 230px;
}

QLabel#AppTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    padding: 20px 16px 4px 16px;
    letter-spacing: 0.5px;
}

QPushButton.NavButton {
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

QPushButton.NavButton:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

QPushButton.NavButton:checked, QPushButton.NavButton.active {
    background-color: #1d4ed8;
    color: #ffffff;
    font-weight: 700;
    border-left: 4px solid #38bdf8;
}

/* Main Content Area */
QFrame#ContentFrame {
    background-color: #0b0f19;
}

/* Cards & Containers */
QFrame.Card {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 20px;
}

QFrame.Card:hover {
    border-color: #3b82f6;
}

QLabel {
    color: #f1f5f9;
}

QLabel.PageHeader {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 4px;
}

QLabel.SectionHeader {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
}

QLabel.SubHeader {
    font-size: 16px;
    font-weight: 700;
    color: #38bdf8;
}

QLabel.StatValue {
    font-size: 32px;
    font-weight: 800;
    color: #38bdf8;
}

QLabel.StatLabel {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Primary & Action Buttons */
QPushButton {
    background-color: #1e293b;
    color: #ffffff !important;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0f172a;
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

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    color: #ffffff;
    font-size: 13px;
}

QComboBox {
    background-color: #0f172a;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 8px 36px 8px 14px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    min-height: 22px;
}

QComboBox:hover {
    border: 1px solid #60a5fa;
    background-color: #1e293b;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid #38bdf8;
    background-color: #1e293b;
    color: #ffffff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    border-left: 1px solid #334155;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background-color: #1e293b;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #38bdf8;
    width: 0px;
    height: 0px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    color: #ffffff;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    outline: 0px;
    padding: 6px;
}

QComboBox QAbstractItemView::item {
    background-color: #0f172a;
    color: #f8fafc;
    min-height: 32px;
    padding: 6px 14px;
    border-radius: 4px;
    margin: 2px 0;
}

QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {
    background-color: #0284c7 !important;
    color: #ffffff !important;
    font-weight: bold;
}

/* Wizard Step Breadcrumb Navigation Bar */
QFrame.StepHeader {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 14px;
}

QLabel.StepPill {
    background-color: #1e293b;
    color: #94a3b8;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 6px;
}

QLabel.StepPillActive {
    background-color: #0284c7;
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 6px;
    border: 1px solid #38bdf8;
}

/* Radio Buttons & CheckBoxes */
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

/* Lists & Tables */
QListWidget, QTableWidget {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #f8fafc;
    gridline-color: #1e293b;
}

QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #1e293b;
    color: #f8fafc;
}

QListWidget::item:hover {
    background-color: #1e293b;
    color: #ffffff;
}

QListWidget::item:selected {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 700;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #1e293b;
    border-radius: 8px;
    background-color: #0f172a;
    text-align: center;
    color: #ffffff;
    font-weight: 700;
    height: 22px;
}

QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 7px;
}

/* ScrollBars */
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #0b0f19;
    border: none;
}

QScrollBar:vertical {
    width: 10px;
}

QScrollBar:horizontal {
    height: 10px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #334155;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #475569;
}

/* ToolTips */
QToolTip {
    background-color: #1e293b;
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 6px;
    padding: 6px;
}
"""
