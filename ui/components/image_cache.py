"""
Thumbnail / Cover Pixmap Cache & Asynchronous Image Loader.

Decodes images at their display size on background threads and caches the scaled
result in Qt's global QPixmapCache. This completely eliminates UI thread freezing
when loading galleries, search results, profile cards, and duplicate sets.
"""

from collections.abc import Callable
import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath, QPixmap, QPixmapCache

logger = logging.getLogger(__name__)

# Cache limit = 64 MB
QPixmapCache.setCacheLimit(65536)


def decode_cover_qimage(path: str | None, width: int, height: int, radius: int = 0) -> QImage | None:
    """
    Decode and scale an image to cover a (width x height) box, optionally applying
    rounded corner clipping. Thread-safe: uses only QImage and QPainter on QImage.
    """
    if not path or width <= 0 or height <= 0:
        return None

    try:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        orig = reader.size()
        if orig.isValid() and orig.width() > 0 and orig.height() > 0:
            scale = max(width / orig.width(), height / orig.height())
            target_w = max(1, round(orig.width() * scale))
            target_h = max(1, round(orig.height() * scale))
            reader.setScaledSize(QSize(target_w, target_h))

        image = reader.read()
        if image.isNull():
            # Fallback to domain load_image for RAW/HEIC/TIFF formats if QImageReader fails
            from domain.image_loader import load_image
            pil_img, _ = load_image(Path(path))
            if pil_img is not None:
                rgb_pil = pil_img.convert("RGBA")
                data = rgb_pil.tobytes("raw", "RGBA")
                raw_qimg = QImage(data, rgb_pil.width, rgb_pil.height, rgb_pil.width * 4, QImage.Format_RGBA8888)
                scale = max(width / raw_qimg.width(), height / raw_qimg.height())
                target_w = max(1, round(raw_qimg.width() * scale))
                target_h = max(1, round(raw_qimg.height() * scale))
                image = raw_qimg.scaled(target_w, target_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            else:
                return None
    except Exception as e:
        logger.debug(f"Could not decode thumbnail for {path}: {e}")
        return None

    if image.isNull():
        return None

    # Crop and apply rounded corners
    target = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    target.fill(Qt.transparent)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    if radius > 0:
        path_obj = QPainterPath()
        path_obj.addRoundedRect(0, 0, width, height, radius, radius)
        painter.setClipPath(path_obj)

    x_off = max(0, (image.width() - width) // 2)
    y_off = max(0, (image.height() - height) // 2)
    painter.drawImage(-x_off, -y_off, image)
    painter.end()

    return target


def load_cover_pixmap(path: str | None, width: int, height: int, radius: int = 0) -> QPixmap | None:
    """
    Return a QPixmap decoded and scaled to cover a width x height box.
    Uses QPixmapCache to avoid re-decoding.
    """
    if not path or width <= 0 or height <= 0:
        return None

    try:
        mtime = int(os.path.getmtime(path))
    except OSError:
        return None

    key = f"cover|{path}|{mtime}|{width}x{height}|r{radius}"
    cached = QPixmapCache.find(key)
    if cached is not None and not cached.isNull():
        return cached

    qimg = decode_cover_qimage(path, width, height, radius=radius)
    if qimg is None or qimg.isNull():
        return None

    pixmap = QPixmap.fromImage(qimg)
    if pixmap.isNull():
        return None

    QPixmapCache.insert(key, pixmap)
    return pixmap


class _ThumbnailWorkerSignals(QObject):
    finished = Signal(str, str, QImage)  # cache_key, path, qimage


class _ThumbnailRunnable(QRunnable):
    def __init__(self, path: str, width: int, height: int, radius: int, cache_key: str, signals: _ThumbnailWorkerSignals):
        super().__init__()
        self.path = path
        self.width = width
        self.height = height
        self.radius = radius
        self.cache_key = cache_key
        self.signals = signals
        self.setAutoDelete(True)

    def run(self):
        qimg = decode_cover_qimage(self.path, self.width, self.height, self.radius)
        if qimg is not None and not qimg.isNull():
            self.signals.finished.emit(self.cache_key, self.path, qimg)


class AsyncThumbnailLoader(QObject):
    """
    Non-blocking, background thumbnail loader and cache manager.
    Delivers decoded and rounded thumbnails directly to callbacks on the GUI thread.
    """

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)
        self.signals = _ThumbnailWorkerSignals()
        self.signals.finished.connect(self._on_worker_finished)
        self._pending_callbacks: dict[str, list[Callable[[QPixmap], None]]] = {}

    def load_thumbnail_async(
        self,
        path: str | None,
        width: int,
        height: int,
        callback: Callable[[QPixmap], None],
        radius: int = 0,
    ) -> bool:
        """
        Request a thumbnail asynchronously.
        If already cached in QPixmapCache, invokes callback immediately and returns True.
        Otherwise, queues a background task and returns False.
        """
        if not path or width <= 0 or height <= 0:
            return False

        try:
            mtime = int(os.path.getmtime(path))
        except OSError:
            return False

        cache_key = f"cover|{path}|{mtime}|{width}x{height}|r{radius}"

        # 1. Fast Cache Hit
        cached = QPixmapCache.find(cache_key)
        if cached is not None and not cached.isNull():
            callback(cached)
            return True

        # 2. Queue async background task
        if cache_key in self._pending_callbacks:
            self._pending_callbacks[cache_key].append(callback)
            return False

        self._pending_callbacks[cache_key] = [callback]
        runnable = _ThumbnailRunnable(path, width, height, radius, cache_key, self.signals)
        self.thread_pool.start(runnable)
        return False

    def _on_worker_finished(self, cache_key: str, path: str, qimg: QImage):
        callbacks = self._pending_callbacks.pop(cache_key, [])
        if not callbacks or qimg.isNull():
            return

        pixmap = QPixmap.fromImage(qimg)
        if not pixmap.isNull():
            QPixmapCache.insert(cache_key, pixmap)
            for cb in callbacks:
                try:
                    cb(pixmap)
                except Exception as e:
                    logger.debug(f"Error invoking thumbnail callback: {e}")


_GLOBAL_ASYNC_LOADER: AsyncThumbnailLoader | None = None


def get_async_thumbnail_loader() -> AsyncThumbnailLoader:
    """Retrieve or create singleton AsyncThumbnailLoader."""
    global _GLOBAL_ASYNC_LOADER
    if _GLOBAL_ASYNC_LOADER is None:
        _GLOBAL_ASYNC_LOADER = AsyncThumbnailLoader()
    return _GLOBAL_ASYNC_LOADER
