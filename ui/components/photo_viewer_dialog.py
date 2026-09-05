"""
Interactive Photo Viewer & Lightbox Dialog.

Provides full-screen image inspection with smooth zoom/pan, navigation (next/prev),
metadata display (dimensions, score, folder), keyboard shortcuts, and single-photo saving.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QImageReader, QKeySequence, QPainter, QPixmap, QShortcut, QWheelEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.find_photos_service import FindPhotosService


class ZoomableGraphicsView(QGraphicsView):
    """QGraphicsView with smooth mouse wheel zooming, centered toolbar zooming, and rotation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("background-color: #050811; border: none;")

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom_factor = 1.0

    def set_pixmap(self, pixmap: QPixmap):
        self._scene.clear()
        self.resetTransform()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fit_to_window()

    def fit_to_window(self):
        if self._pixmap_item:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._zoom_factor = 1.0

    def actual_size(self):
        """Reset zoom to 100% actual pixel dimensions."""
        self.resetTransform()
        self._zoom_factor = 1.0

    def zoom_in(self):
        """Zoom in towards view center."""
        if self._zoom_factor >= 20.0:
            return
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.scale(1.25, 1.25)
        self._zoom_factor *= 1.25

    def zoom_out(self):
        """Zoom out towards view center."""
        if self._zoom_factor <= 0.05:
            return
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.scale(0.8, 0.8)
        self._zoom_factor *= 0.8

    def reset_zoom(self):
        self.fit_to_window()

    def rotate_left(self):
        """Rotate viewport 90 degrees counter-clockwise."""
        self.rotate(-90)
        self.fit_to_window()

    def rotate_right(self):
        """Rotate viewport 90 degrees clockwise."""
        self.rotate(90)
        self.fit_to_window()

    def wheelEvent(self, event: QWheelEvent):
        # Anchor under mouse cursor for interactive wheel zoom
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        if event.angleDelta().y() > 0:
            if self._zoom_factor < 20.0:
                self.scale(1.25, 1.25)
                self._zoom_factor *= 1.25
        else:
            if self._zoom_factor > 0.05:
                self.scale(0.8, 0.8)
                self._zoom_factor *= 0.8


class PhotoViewerDialog(QDialog):
    """
    Rich modal Lightbox Dialog for inspecting photos with zoom/pan, next/previous navigation,
    metadata inspector, and 1-click download.
    """

    def __init__(
        self,
        photos_list: list[dict[str, Any]],
        initial_index: int = 0,
        parent: QWidget | None = None,
        save_service: FindPhotosService | None = None,
    ):
        super().__init__(parent)
        self.photos_list = photos_list
        self.current_index = max(0, min(initial_index, len(photos_list) - 1)) if photos_list else 0
        self.save_service = save_service or FindPhotosService()

        self.setWindowTitle("Photo Viewer — Photo Face AI")
        self.resize(1000, 720)
        self.setMinimumSize(700, 500)
        self.setStyleSheet("background-color: #080c14; color: #ffffff;")

        self._setup_ui()
        self._setup_shortcuts()
        self._load_current_photo()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Toolbar
        header_bar = QFrame()
        header_bar.setStyleSheet("background-color: #0f172a; border-bottom: 1px solid #1e293b; padding: 6px 14px;")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(12)

        self.lbl_title = QLabel("Photo Viewer")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        header_layout.addWidget(self.lbl_title)

        self.lbl_badge_score = QLabel("")
        self.lbl_badge_score.setStyleSheet(
            "background-color: #064e3b; color: #34d399; font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 6px; border: 1px solid #10b981;"
        )
        header_layout.addWidget(self.lbl_badge_score)

        self.lbl_counter = QLabel("1 of 1")
        self.lbl_counter.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        header_layout.addWidget(self.lbl_counter)

        header_layout.addStretch()

        # Icon buttons style
        btn_icon_style = (
            "QPushButton { background-color: #1e293b; color: #ffffff; border: 1px solid #334155; border-radius: 6px; font-size: 15px; font-weight: bold; }"
            "QPushButton:hover { background-color: #334155; color: #38bdf8; border-color: #38bdf8; }"
        )

        # Zoom Controls (Icon-Only)
        btn_zoom_in = QPushButton("➕")
        btn_zoom_in.setToolTip("Zoom In (+ or Scroll Up)")
        btn_zoom_in.setCursor(Qt.PointingHandCursor)
        btn_zoom_in.setFixedSize(34, 34)
        btn_zoom_in.setStyleSheet(btn_icon_style)
        btn_zoom_in.clicked.connect(self._zoom_in)
        header_layout.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("➖")
        btn_zoom_out.setToolTip("Zoom Out (- or Scroll Down)")
        btn_zoom_out.setCursor(Qt.PointingHandCursor)
        btn_zoom_out.setFixedSize(34, 34)
        btn_zoom_out.setStyleSheet(btn_icon_style)
        btn_zoom_out.clicked.connect(self._zoom_out)
        header_layout.addWidget(btn_zoom_out)

        btn_fit = QPushButton("⊡")
        btn_fit.setToolTip("Fit to Window (F or 0)")
        btn_fit.setCursor(Qt.PointingHandCursor)
        btn_fit.setFixedSize(34, 34)
        btn_fit.setStyleSheet(btn_icon_style)
        btn_fit.clicked.connect(self._fit_to_window)
        header_layout.addWidget(btn_fit)

        # Rotate Control (Single Icon-Only Button)
        btn_rotate = QPushButton("⟳")
        btn_rotate.setToolTip("Rotate 90° (R)")
        btn_rotate.setCursor(Qt.PointingHandCursor)
        btn_rotate.setFixedSize(34, 34)
        btn_rotate.setStyleSheet(btn_icon_style)
        btn_rotate.clicked.connect(self._rotate)
        header_layout.addWidget(btn_rotate)

        # Close button
        btn_close = QPushButton("✕")
        btn_close.setToolTip("Close (Esc)")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedSize(34, 34)
        btn_close.setStyleSheet("background-color: #dc2626; color: #ffffff; border-radius: 6px; font-size: 15px; font-weight: bold;")
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)

        main_layout.addWidget(header_bar)

        # 2. Main Viewport & Navigation Arrows
        viewport_container = QWidget()
        viewport_layout = QHBoxLayout(viewport_container)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)

        # Left Nav Button
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setToolTip("Previous Photo (Left Arrow)")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setFixedSize(48, 80)
        self.btn_prev.setStyleSheet(
            "QPushButton { background-color: rgba(15, 23, 42, 0.7); color: #ffffff; border: none; font-size: 20px; font-weight: bold; border-top-right-radius: 8px; border-bottom-right-radius: 8px; }"
            "QPushButton:hover { background-color: #0284c7; }"
            "QPushButton:disabled { color: #475569; background-color: transparent; }"
        )
        self.btn_prev.clicked.connect(self._prev_photo)

        # Graphics Canvas
        self.view = ZoomableGraphicsView(self)

        # Right Nav Button
        self.btn_next = QPushButton("▶")
        self.btn_next.setToolTip("Next Photo (Right Arrow)")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFixedSize(48, 80)
        self.btn_next.setStyleSheet(
            "QPushButton { background-color: rgba(15, 23, 42, 0.7); color: #ffffff; border: none; font-size: 20px; font-weight: bold; border-top-left-radius: 8px; border-bottom-left-radius: 8px; }"
            "QPushButton:hover { background-color: #0284c7; }"
            "QPushButton:disabled { color: #475569; background-color: transparent; }"
        )
        self.btn_next.clicked.connect(self._next_photo)

        viewport_layout.addWidget(self.btn_prev)
        viewport_layout.addWidget(self.view, 1)
        viewport_layout.addWidget(self.btn_next)

        main_layout.addWidget(viewport_container, 1)

        # 3. Bottom Info & Actions Bar
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("background-color: #0f172a; border-top: 1px solid #1e293b; padding: 6px 14px;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(14, 8, 14, 8)
        bottom_layout.setSpacing(14)

        self.lbl_path_info = QLabel("Path:")
        self.lbl_path_info.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.lbl_path_info.setWordWrap(True)
        bottom_layout.addWidget(self.lbl_path_info, 1)

        btn_open_folder = QPushButton("📂 Open Location")
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.setFixedHeight(34)
        btn_open_folder.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; border: 1px solid #3b82f6; border-radius: 6px; padding: 0 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_open_folder.clicked.connect(self._open_containing_folder)
        bottom_layout.addWidget(btn_open_folder)

        btn_save_this = QPushButton("💾 Save Photo")
        btn_save_this.setCursor(Qt.PointingHandCursor)
        btn_save_this.setFixedHeight(34)
        btn_save_this.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; border: none; border-radius: 6px; padding: 0 16px; font-weight: 700; font-size: 12px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        btn_save_this.clicked.connect(self._save_current_photo)
        bottom_layout.addWidget(btn_save_this)

        main_layout.addWidget(bottom_bar)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Left), self, self._prev_photo)
        QShortcut(QKeySequence(Qt.Key_Right), self, self._next_photo)
        QShortcut(QKeySequence(Qt.Key_Plus), self, self._zoom_in)
        QShortcut(QKeySequence(Qt.Key_Equal), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence(Qt.Key_Minus), self, self._zoom_out)
        QShortcut(QKeySequence(Qt.Key_Underscore), self, self._zoom_out)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)
        QShortcut(QKeySequence(Qt.Key_F), self, self._fit_to_window)
        QShortcut(QKeySequence(Qt.Key_0), self, self._fit_to_window)
        QShortcut(QKeySequence(Qt.Key_1), self, self._actual_size)
        QShortcut(QKeySequence(Qt.Key_L), self, self._rotate_left)
        QShortcut(QKeySequence(Qt.Key_BracketLeft), self, self._rotate_left)
        QShortcut(QKeySequence(Qt.Key_R), self, self._rotate_right)
        QShortcut(QKeySequence(Qt.Key_BracketRight), self, self._rotate_right)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)

    def _load_current_photo(self):
        if not self.photos_list or self.current_index < 0 or self.current_index >= len(self.photos_list):
            return

        item = self.photos_list[self.current_index]
        path_str = item.get("path", "")
        p = Path(path_str)

        self.lbl_title.setText(f"📷 {item.get('filename', p.name)}")
        score = item.get("match_score", 0.0)
        self.lbl_badge_score.setText(f"🎯 {score}% Match")
        self.lbl_counter.setText(f"{self.current_index + 1} of {len(self.photos_list)}")

        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.photos_list) - 1)

        if p.exists():
            pix = QPixmap(str(p))
            if not pix.isNull():
                self.view.set_pixmap(pix)
                dims = f"{pix.width()} × {pix.height()} px"
                self.lbl_path_info.setText(f"<b>Path:</b> {p}  •  <b>Size:</b> {dims}  •  <b>Modified:</b> {item.get('formatted_mtime', 'N/A')}")
            else:
                self.lbl_path_info.setText(f"<b>Path:</b> {p} (Unreadable image format)")
        else:
            self.lbl_path_info.setText(f"<b>File not found:</b> {p}")

    def _zoom_in(self):
        self.view.zoom_in()

    def _zoom_out(self):
        self.view.zoom_out()

    def _fit_to_window(self):
        self.view.fit_to_window()

    def _actual_size(self):
        self.view.actual_size()

    def _rotate(self):
        """Rotate photo 90 degrees clockwise."""
        self.view.rotate_right()

    def _rotate_left(self):
        self.view.rotate_left()

    def _rotate_right(self):
        self.view.rotate_right()

    def _prev_photo(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_photo()

    def _next_photo(self):
        if self.current_index < len(self.photos_list) - 1:
            self.current_index += 1
            self._load_current_photo()

    def _open_containing_folder(self):
        if not self.photos_list:
            return
        item = self.photos_list[self.current_index]
        p = Path(item.get("path", ""))
        if not p.exists():
            return
        folder = str(p.parent)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def _save_current_photo(self):
        if not self.photos_list:
            return
        item = self.photos_list[self.current_index]
        src_path = item.get("path", "")
        p = Path(src_path)
        if not p.exists():
            QMessageBox.warning(self, "Error", f"Source file does not exist: {p}")
            return

        dest_folder = QFileDialog.getExistingDirectory(self, f"Choose Destination Folder to Save {p.name}")
        if not dest_folder:
            return

        success, target_path, msg = self.save_service.save_single_photo(src_path, dest_folder)
        if success and target_path:
            QMessageBox.information(
                self,
                "Photo Saved",
                f"✨ Successfully saved photo to:\n\n📁 {target_path}",
            )
        else:
            QMessageBox.warning(self, "Save Failed", f"Could not save photo:\n{msg}")
