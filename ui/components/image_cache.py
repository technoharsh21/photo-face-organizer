"""
Thumbnail / Cover Pixmap Cache.

Decodes images at (near) their display size instead of loading the full-
resolution source, and caches the scaled result in Qt's global QPixmapCache.
This avoids re-decoding multi-MB photos into tiny avatars on every refresh and
re-scaling them on every repaint — the main non-AI UI cost in this app.
"""

import os

from PySide6.QtCore import QSize
from PySide6.QtGui import QImageReader, QPixmap, QPixmapCache

# Bump the global pixmap cache well above the ~10MB default so many thumbnails
# stay resident across page navigation and list refreshes.
QPixmapCache.setCacheLimit(65536)  # KB = 64 MB


def load_cover_pixmap(path: str | None, width: int, height: int) -> QPixmap | None:
    """
    Return a QPixmap decoded and scaled to *cover* a width x height box
    (aspect preserved, large enough to fill the box), cached by path+mtime+size.
    Returns None if the path is missing/unreadable.
    """
    if not path or width <= 0 or height <= 0:
        return None
    try:
        mtime = int(os.path.getmtime(path))
    except OSError:
        return None

    key = f"cover|{path}|{mtime}|{width}x{height}"
    cached = QPixmapCache.find(key)
    if cached is not None and not cached.isNull():
        return cached

    reader = QImageReader(path)
    reader.setAutoTransform(True)
    orig = reader.size()
    if orig.isValid() and orig.width() > 0 and orig.height() > 0:
        scale = max(width / orig.width(), height / orig.height())
        target_w = max(1, round(orig.width() * scale))
        target_h = max(1, round(orig.height() * scale))
        reader.setScaledSize(QSize(target_w, target_h))  # cover box, aspect preserved

    image = reader.read()
    if image.isNull():
        return None

    pixmap = QPixmap.fromImage(image)
    if pixmap.isNull():
        return None
    QPixmapCache.insert(key, pixmap)
    return pixmap
