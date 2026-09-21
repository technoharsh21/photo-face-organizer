"""
Skeleton shimmer placeholders for in-flight loading states.

QSS cannot animate gradients, so the shimmer band is painted in Python and
moved with a QTimer while the widget is visible. Use SkeletonBlock as a drop-in
placeholder sized to match the content that will replace it, or compose several
blocks in a SkeletonCard for list-row / grid-card previews.
"""

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

_BASE = QColor("#1e293b")
_HIGHLIGHT = QColor(51, 65, 85, 200)  # #334155 with alpha
_BAND_WIDTH = 160.0


class SkeletonBlock(QFrame):
    """A single shimmering rounded rectangle."""

    def __init__(self, width: int = -1, height: int = 16, radius: int = 6, parent=None):
        super().__init__(parent)
        if width > 0:
            self.setFixedSize(width, height)
        else:
            self.setFixedHeight(height)
        self._radius = radius
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 fps
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event):
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self):
        w = max(self.width(), 1)
        self._phase = (self._phase + 14.0) % (w + _BAND_WIDTH)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        path_band = QRectF(-_BAND_WIDTH + self._phase, 0, _BAND_WIDTH, self.height())
        grad = QLinearGradient(path_band.topLeft(), path_band.topRight())
        grad.setColorAt(0.0, QColor(_BASE))
        grad.setColorAt(0.5, _HIGHLIGHT)
        grad.setColorAt(1.0, QColor(_BASE))

        p.setClipToRoundRect(rect, self._radius, self._radius)
        p.fillRect(rect, grad)
        p.end()


class SkeletonCard(QWidget):
    """Common placeholder shapes composed from SkeletonBlocks."""

    @staticmethod
    def image_tile(size: int = 160, parent=None) -> SkeletonBlock:
        return SkeletonBlock(size, size, radius=12, parent=parent)

    @staticmethod
    def list_row(parent=None) -> QWidget:
        row = QWidget(parent)
        row.setAttribute(Qt.WA_TranslucentBackground)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)
        layout.addWidget(SkeletonBlock(44, 44, radius=8), 0)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(SkeletonBlock(-1, 14, radius=5))
        col.addWidget(SkeletonBlock(-1, 10, radius=5))
        layout.addLayout(col, 1)
        return row

    @staticmethod
    def text_lines(count: int = 3, parent=None) -> QWidget:
        col = QWidget(parent)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for i in range(count):
            # last line is intentionally shorter to read like text
            block = SkeletonBlock(-1 if i < count - 1 else 110, 12, radius=5)
            layout.addWidget(block)
        return col
