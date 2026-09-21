"""
Toast notification system for Photo Face AI.

Non-blocking, slide-in notifications anchored to the bottom-right of a host
widget (typically the main window). Supports success / error / warning / info
variants with a colored accent border, auto-dismiss, and manual close.
Stacking is capped (3 visible); older toasts are dismissed to make room.
"""

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.components.icons import get_icon

_TOAST_ICONS = {
    "success": ("check_circle", "#10b981"),
    "error": ("x_circle", "#ef4444"),
    "warning": ("alert_triangle", "#f59e0b"),
    "info": ("info_circle", "#38bdf8"),
}


class Toast(QFrame):
    """A single notification card. Styling via QSS #Toast + toastType property."""

    def __init__(self, toast_type: str, title: str, body: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("toastType", toast_type)
        self.setFixedWidth(330)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 8, 10)
        layout.setSpacing(10)

        icon_name, icon_color = _TOAST_ICONS.get(toast_type, _TOAST_ICONS["info"])
        icon_label = QLabel()
        icon_label.setPixmap(get_icon(icon_name, color=icon_color, size=20).pixmap(20, 20))
        icon_label.setFixedWidth(20)
        layout.addWidget(icon_label, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("ToastTitle")
        title_lbl.setWordWrap(True)
        text_col.addWidget(title_lbl)
        if body:
            body_lbl = QLabel(body)
            body_lbl.setObjectName("ToastBody")
            body_lbl.setWordWrap(True)
            text_col.addWidget(body_lbl)
        layout.addLayout(text_col, 1)

        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("ToastClose")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedSize(22, 22)
        layout.addWidget(self.btn_close, 0, Qt.AlignTop)


class ToastManager(QObject):
    """Owns the toast stack and its slide/fade animations for a host widget."""

    MAX_VISIBLE = 3

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.host = host
        self._toasts: list[Toast] = []
        host.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.host and event.type() == QEvent.Resize:
            self._reposition_all()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    def show(self, title: str, body: str = "", toast_type: str = "info", duration_ms: int = 4000):
        """Display a toast. `toast_type` is success|error|warning|info."""
        while len(self._toasts) >= self.MAX_VISIBLE:
            self._dismiss(self._toasts[0], immediate=True)

        toast = Toast(toast_type, title, body, parent=self.host)
        toast.btn_close.clicked.connect(lambda: self._dismiss(toast))
        toast.adjustSize()
        self._toasts.append(toast)

        target = self._slot_pos(len(self._toasts) - 1)
        start = QPoint(self.host.width() + 20, target.y())
        toast.move(start)
        toast.show()
        toast.raise_()

        anim = QPropertyAnimation(toast, b"pos", self)
        anim.setDuration(260)
        anim.setStartValue(start)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        # keep a reference so the animation isn't garbage collected mid-flight
        toast._slide_anim = anim

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, lambda: self._dismiss(toast))
        self._reposition_all()

    # ------------------------------------------------------------------
    def _slot_pos(self, index: int) -> QPoint:
        """Bottom-right anchored slot; index 0 is the bottom-most toast."""
        margin = 16
        gap = 10
        y = self.host.height() - margin
        for i in range(len(self._toasts) - 1, index - 1, -1):
            t = self._toasts[i]
            y -= t.height()
            if i == index:
                break
            y -= gap
        x = self.host.width() - margin - 330
        return QPoint(max(x, margin), max(y, margin))

    def _reposition_all(self):
        for i, toast in enumerate(self._toasts):
            toast.move(self._slot_pos(i))

    def _dismiss(self, toast: Toast, immediate: bool = False):
        if toast not in self._toasts:
            return
        self._toasts.remove(toast)
        if immediate:
            toast.deleteLater()
            self._reposition_all()
            return

        effect = QGraphicsOpacityEffect(toast)
        toast.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity", self)
        fade.setDuration(200)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InQuad)
        fade.finished.connect(toast.deleteLater)
        fade.start()
        toast._fade_anim = fade
        self._reposition_all()
