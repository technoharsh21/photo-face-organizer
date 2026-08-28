"""
UI Stylesheet & Theme Module for PySide6.

Provides a clean, modern, high-contrast desktop dark-themed stylesheet for Windows and Linux.
"""

STYLESHEET = """
/* Global Window & Base Controls */
QMainWindow, QDialog, QMessageBox, QInputDialog, QFileDialog {
    background-color: #1e1e24;
    color: #f0f0f0;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

QWidget {
    color: #e0e0e0;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
QFrame#Sidebar {
    background-color: #141418;
    border-right: 1px solid #2a2a32;
    min-width: 220px;
    max-width: 220px;
}

QLabel#AppTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
    padding: 18px 12px;
}

QPushButton.NavButton {
    background-color: transparent;
    color: #a0a0b0;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
}

QPushButton.NavButton:hover {
    background-color: #2a2a36;
    color: #ffffff;
}

QPushButton.NavButton:checked, QPushButton.NavButton.active {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}

/* Main Content Area */
QFrame#ContentFrame {
    background-color: #1e1e24;
}

/* Cards & Containers */
QFrame.Card {
    background-color: #25252e;
    border: 1px solid #333340;
    border-radius: 8px;
    padding: 16px;
}

QFrame.Card:hover {
    border: 1px solid #3b82f6;
}

QLabel {
    color: #f0f0f0;
}

QLabel.PageHeader {
    font-size: 22px;
    font-weight: bold;
    color: #ffffff;
    margin-bottom: 8px;
}

QLabel.SectionHeader {
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
}

QLabel.SubHeader {
    font-size: 16px;
    font-weight: bold;
    color: #3b82f6;
}

QLabel.StatValue {
    font-size: 28px;
    font-weight: bold;
    color: #3b82f6;
}

QLabel.StatLabel {
    font-size: 12px;
    color: #a0a0b8;
    text-transform: uppercase;
}

/* Primary & Action Buttons */
QPushButton {
    background-color: #2d2d38;
    color: #ffffff;
    border: 1px solid #404050;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383846;
    color: #ffffff;
}

QPushButton.PrimaryButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton.PrimaryButton:hover {
    background-color: #2563eb;
}

QPushButton.PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton.SecondaryButton {
    background-color: #2d2d38;
    color: #f0f0f0;
    border: 1px solid #404050;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 500;
}

QPushButton.SecondaryButton:hover {
    background-color: #383846;
    color: #ffffff;
}

QPushButton.DangerButton {
    background-color: #ef4444;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}

QPushButton.DangerButton:hover {
    background-color: #dc2626;
}

/* Inputs, ComboBox, LineEdit, Dialog Elements */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #181820;
    color: #ffffff;
    border: 1px solid #383848;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #3b82f6;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}

QRadioButton, QCheckBox {
    color: #ffffff;
    spacing: 8px;
    font-size: 13px;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QGroupBox {
    color: #ffffff;
    border: 1px solid #383848;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #ffffff;
}

/* Dialogs & Message Boxes styling */
QMessageBox QLabel, QInputDialog QLabel {
    color: #ffffff;
    font-size: 13px;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 6px 14px;
}

/* Lists & Tables */
QListWidget, QTableWidget, QTreeWidget {
    background-color: #181820;
    border: 1px solid #2e2e3a;
    border-radius: 6px;
    color: #f0f0f0;
    gridline-color: #2e2e3a;
}

QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #22222c;
    color: #f0f0f0;
}

QListWidget::item:hover {
    background-color: #242432;
    color: #ffffff;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}

QHeaderView::section {
    background-color: #22222c;
    color: #f0f0f0;
    font-weight: 600;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #333340;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #333340;
    border-radius: 6px;
    background-color: #181820;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 5px;
}

/* ScrollBars */
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #181820;
    border: none;
    margin: 0px;
}

QScrollBar:vertical {
    width: 10px;
}

QScrollBar:horizontal {
    height: 10px;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #333344;
    border-radius: 5px;
    min-height: 20px;
    min-width: 20px;
}

QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background-color: #4f4f66;
}

/* ToolTips */
QToolTip {
    background-color: #282836;
    color: #ffffff;
    border: 1px solid #3b82f6;
    padding: 4px 8px;
    border-radius: 4px;
}
"""
