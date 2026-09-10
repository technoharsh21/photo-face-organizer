"""
Interactive Photo Viewer & Lightbox Dialog.

Provides full-screen image inspection with smooth zoom/pan, navigation (next/prev),
metadata display (dimensions, score, folder), keyboard shortcuts, and single-photo saving.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRectF, QSize, Qt, QThread, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QImage,
    QImageReader,
    QKeySequence,
    QPainter,
    QPixmap,
    QResizeEvent,
    QShortcut,
    QShowEvent,
    QWheelEvent,
)
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

from domain.image_loader import load_image
from services.find_photos_service import FindPhotosService
from ui.components.icons import get_icon
from ui.components.image_cache import load_cover_pixmap


class AsyncPhotoLoader(QThread):
    """Background loader for full-resolution photos to prevent UI freezes."""

    loaded = Signal(str, QImage, str)  # path, qimage, dims_str
    failed = Signal(str, str)          # path, error_message

    def __init__(self, photo_path: str):
        super().__init__()
        self.photo_path = photo_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            return

        p = Path(self.photo_path)
        if not p.exists():
            self.failed.emit(self.photo_path, "File not found")
            return

        try:
            # 1. Fast direct decode via QImageReader
            reader = QImageReader(str(p))
            reader.setAutoTransform(True)
            qimg = reader.read()
            if not qimg.isNull() and not self._is_cancelled:
                dims = f"{qimg.width()} × {qimg.height()} px"
                self.loaded.emit(self.photo_path, qimg, dims)
                return

            # 2. Fallback for RAW, HEIC, TIFF, etc. via domain load_image
            if self._is_cancelled:
                return
            pil_img, err = load_image(p)
            if pil_img is not None and not self._is_cancelled:
                import io
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                qimg = QImage()
                qimg.loadFromData(buf.getvalue())
                if not qimg.isNull() and not self._is_cancelled:
                    dims = f"{pil_img.width} × {pil_img.height()} px"
                    self.loaded.emit(self.photo_path, qimg, dims)
                    return
            if not self._is_cancelled:
                self.failed.emit(self.photo_path, err or "Unreadable image format")
        except (OSError, ValueError, RuntimeError) as e:
            if not self._is_cancelled:
                self.failed.emit(self.photo_path, str(e))


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

    def set_pixmap(self, pixmap: QPixmap, is_preview: bool = False):
        self._scene.clear()
        self.resetTransform()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fit_to_window()

    def set_full_pixmap(self, pixmap: QPixmap):
        """Update scene with full-resolution image while preserving current view / zoom."""
        if not self._pixmap_item:
            self.set_pixmap(pixmap)
            return

        # Seamlessly swap pixmap on the existing item without clearing transformation
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        if abs(self._zoom_factor - 1.0) < 0.01:
            self.fit_to_window()

    def fit_to_window(self):
        if self._pixmap_item and self.viewport().width() > 10 and self.viewport().height() > 10:
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

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if abs(self._zoom_factor - 1.0) < 0.01:
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
        self._loader_thread: AsyncPhotoLoader | None = None

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
            "QPushButton { background-color: #1e293b; color: #ffffff; border: 1px solid #334155; border-radius: 6px; padding: 0px; }"
            "QPushButton:hover { background-color: #334155; border-color: #38bdf8; }"
            "QPushButton:pressed { background-color: #0f172a; }"
        )

        # Zoom Controls (Icon-Only)
        btn_zoom_in = QPushButton()
        btn_zoom_in.setIcon(get_icon("zoom_in", color="#ffffff", size=20))
        btn_zoom_in.setIconSize(QSize(18, 18))
        btn_zoom_in.setToolTip("Zoom In (+ or Scroll Up)")
        btn_zoom_in.setCursor(Qt.PointingHandCursor)
        btn_zoom_in.setFixedSize(34, 34)
        btn_zoom_in.setStyleSheet(btn_icon_style)
        btn_zoom_in.clicked.connect(self._zoom_in)
        header_layout.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton()
        btn_zoom_out.setIcon(get_icon("zoom_out", color="#ffffff", size=20))
        btn_zoom_out.setIconSize(QSize(18, 18))
        btn_zoom_out.setToolTip("Zoom Out (- or Scroll Down)")
        btn_zoom_out.setCursor(Qt.PointingHandCursor)
        btn_zoom_out.setFixedSize(34, 34)
        btn_zoom_out.setStyleSheet(btn_icon_style)
        btn_zoom_out.clicked.connect(self._zoom_out)
        header_layout.addWidget(btn_zoom_out)

        btn_fit = QPushButton()
        btn_fit.setIcon(get_icon("zoom_fit", color="#ffffff", size=20))
        btn_fit.setIconSize(QSize(18, 18))
        btn_fit.setToolTip("Fit to Window (F or 0)")
        btn_fit.setCursor(Qt.PointingHandCursor)
        btn_fit.setFixedSize(34, 34)
        btn_fit.setStyleSheet(btn_icon_style)
        btn_fit.clicked.connect(self._fit_to_window)
        header_layout.addWidget(btn_fit)

        btn_actual = QPushButton()
        btn_actual.setIcon(get_icon("zoom_actual", color="#ffffff", size=20))
        btn_actual.setIconSize(QSize(18, 18))
        btn_actual.setToolTip("Actual Size 100% (1)")
        btn_actual.setCursor(Qt.PointingHandCursor)
        btn_actual.setFixedSize(34, 34)
        btn_actual.setStyleSheet(btn_icon_style)
        btn_actual.clicked.connect(self._actual_size)
        header_layout.addWidget(btn_actual)

        # Rotate Controls (CCW and CW)
        btn_rotate_left = QPushButton()
        btn_rotate_left.setIcon(get_icon("rotate_ccw", color="#ffffff", size=20))
        btn_rotate_left.setIconSize(QSize(18, 18))
        btn_rotate_left.setToolTip("Rotate Left 90° (L or [)")
        btn_rotate_left.setCursor(Qt.PointingHandCursor)
        btn_rotate_left.setFixedSize(34, 34)
        btn_rotate_left.setStyleSheet(btn_icon_style)
        btn_rotate_left.clicked.connect(self._rotate_left)
        header_layout.addWidget(btn_rotate_left)

        btn_rotate_right = QPushButton()
        btn_rotate_right.setIcon(get_icon("rotate_cw", color="#ffffff", size=20))
        btn_rotate_right.setIconSize(QSize(18, 18))
        btn_rotate_right.setToolTip("Rotate Right 90° (R or ])")
        btn_rotate_right.setCursor(Qt.PointingHandCursor)
        btn_rotate_right.setFixedSize(34, 34)
        btn_rotate_right.setStyleSheet(btn_icon_style)
        btn_rotate_right.clicked.connect(self._rotate_right)
        header_layout.addWidget(btn_rotate_right)

        # Close button
        btn_close = QPushButton()
        btn_close.setIcon(get_icon("close", color="#ffffff", size=18))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.setToolTip("Close (Esc)")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedSize(34, 34)
        btn_close.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: 1px solid #b91c1c; border-radius: 6px; padding: 0px; }"
            "QPushButton:hover { background-color: #ef4444; border-color: #f87171; }"
            "QPushButton:pressed { background-color: #991b1b; }"
        )
        btn_close.clicked.connect(self.close)
        header_layout.addWidget(btn_close)

        main_layout.addWidget(header_bar)

        # 2. Main Viewport & Navigation Arrows
        viewport_container = QWidget()
        viewport_layout = QHBoxLayout(viewport_container)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)

        # Left Nav Button
        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(get_icon("chevron_left", color="#ffffff", disabled_color="#475569", size=32))
        self.btn_prev.setIconSize(QSize(28, 28))
        self.btn_prev.setToolTip("Previous Photo (Left Arrow)")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.setFixedSize(48, 80)
        self.btn_prev.setStyleSheet(
            "QPushButton { background-color: rgba(15, 23, 42, 0.7); border: none; border-top-right-radius: 8px; border-bottom-right-radius: 8px; padding: 0px; }"
            "QPushButton:hover { background-color: #0284c7; }"
            "QPushButton:disabled { background-color: transparent; }"
        )
        self.btn_prev.clicked.connect(self._prev_photo)

        # Graphics Canvas
        self.view = ZoomableGraphicsView(self)

        # Right Nav Button
        self.btn_next = QPushButton()
        self.btn_next.setIcon(get_icon("chevron_right", color="#ffffff", disabled_color="#475569", size=32))
        self.btn_next.setIconSize(QSize(28, 28))
        self.btn_next.setToolTip("Next Photo (Right Arrow)")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setFixedSize(48, 80)
        self.btn_next.setStyleSheet(
            "QPushButton { background-color: rgba(15, 23, 42, 0.7); border: none; border-top-left-radius: 8px; border-bottom-left-radius: 8px; padding: 0px; }"
            "QPushButton:hover { background-color: #0284c7; }"
            "QPushButton:disabled { background-color: transparent; }"
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

        btn_open_folder = QPushButton(" Open Location")
        btn_open_folder.setIcon(get_icon("folder_open", color="#38bdf8", size=18))
        btn_open_folder.setIconSize(QSize(16, 16))
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.setFixedHeight(34)
        btn_open_folder.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #38bdf8; border: 1px solid #3b82f6; border-radius: 6px; padding: 0 14px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        btn_open_folder.clicked.connect(self._open_containing_folder)
        bottom_layout.addWidget(btn_open_folder)

        btn_save_this = QPushButton(" Save Photo")
        btn_save_this.setIcon(get_icon("download", color="#ffffff", size=18))
        btn_save_this.setIconSize(QSize(16, 16))
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

        # Cancel any previous async load
        self._cancel_loader()

        item = self.photos_list[self.current_index]
        path_str = item.get("path", "")
        p = Path(path_str)

        self.lbl_title.setText(f"📷 {item.get('filename', p.name)}")
        score = item.get("match_score", 0.0)
        self.lbl_badge_score.setText(f"🎯 {score}% Match")
        self.lbl_counter.setText(f"{self.current_index + 1} of {len(self.photos_list)}")

        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.photos_list) - 1)

        if not p.exists():
            self.lbl_path_info.setText(f"<b>File not found:</b> {p}")
            return

        # 1. Instant preview thumbnail from cache (< 1ms)
        fast_thumb = load_cover_pixmap(path_str, 1200, 900)
        if fast_thumb is not None and not fast_thumb.isNull():
            self.view.set_pixmap(fast_thumb, is_preview=True)
            self.lbl_path_info.setText(f"<b>Path:</b> {p}  •  <b>Loading full resolution...</b>")
        else:
            self.lbl_path_info.setText(f"<b>Path:</b> {p}  •  <b>Loading...</b>")

        # 2. Asynchronously decode full-resolution photo in background
        self._loader_thread = AsyncPhotoLoader(path_str)
        self._loader_thread.loaded.connect(self._on_full_photo_loaded)
        self._loader_thread.failed.connect(self._on_full_photo_failed)
        self._loader_thread.start()

    def _on_full_photo_loaded(self, path: str, qimg: QImage, dims: str):
        if not self.photos_list or self.current_index < 0 or self.current_index >= len(self.photos_list):
            return
        current_item = self.photos_list[self.current_index]
        if current_item.get("path") != path:
            return  # User already navigated to another photo

        pix = QPixmap.fromImage(qimg)
        if not pix.isNull():
            self.view.set_full_pixmap(pix)
            self.lbl_path_info.setText(
                f"<b>Path:</b> {path}  •  <b>Size:</b> {dims}  •  <b>Modified:</b> {current_item.get('formatted_mtime', 'N/A')}"
            )

    def _on_full_photo_failed(self, path: str, error_msg: str):
        if not self.photos_list or self.current_index < 0 or self.current_index >= len(self.photos_list):
            return
        current_item = self.photos_list[self.current_index]
        if current_item.get("path") == path:
            self.lbl_path_info.setText(f"<b>Path:</b> {path} ({error_msg})")

    def _cancel_loader(self):
        if self._loader_thread is not None and self._loader_thread.isRunning():
            self._loader_thread.cancel()
            self._loader_thread.wait(500)
            self._loader_thread = None

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.view.fit_to_window()

    def closeEvent(self, event: QCloseEvent):
        self._cancel_loader()
        super().closeEvent(event)

    def reject(self):
        self._cancel_loader()
        super().reject()

    def accept(self):
        self._cancel_loader()
        super().accept()

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
        except (OSError, subprocess.SubprocessError):
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
