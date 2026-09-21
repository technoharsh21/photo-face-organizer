"""
Spotlight onboarding tour overlay for Photo Face AI.

Renders a dimmed overlay on top of the main window with a rounded "hole"
cut around the current step's target widget, plus an info card with
Skip / Next / Done controls. Steps reference targets lazily so pages and
widgets that are created later still resolve when the step is shown.
"""

from typing import Callable, NamedTuple

from PySide6.QtCore import QEvent, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TourStep(NamedTuple):
    title: str
    body: str
    # Returns the widget to highlight; None renders the card centered.
    target: Callable[[], QWidget | None]


_DIM = QColor(2, 6, 16, 185)
_ACCENT = QColor("#38bdf8")
_CARD_WIDTH = 340


class OnboardingTour(QWidget):
    """Modal-ish overlay child of the host window showing sequential steps."""

    finished = Signal()

    def __init__(self, host: QWidget, steps: list[TourStep]):
        super().__init__(host)
        self._host = host
        self._steps = steps
        self._index = 0

        self.setCursor(Qt.PointingHandCursor)
        host.installEventFilter(self)

        # --- Info card ---
        self.card = QFrame(self)
        self.card.setObjectName("TourCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(8)

        self.lbl_step = QLabel(self.card)
        self.lbl_step.setObjectName("TourStep")
        card_layout.addWidget(self.lbl_step)

        self.lbl_title = QLabel(self.card)
        self.lbl_title.setObjectName("TourTitle")
        self.lbl_title.setWordWrap(True)
        card_layout.addWidget(self.lbl_title)

        self.lbl_body = QLabel(self.card)
        self.lbl_body.setObjectName("TourBody")
        self.lbl_body.setWordWrap(True)
        card_layout.addWidget(self.lbl_body)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_skip = QPushButton("Skip tour")
        self.btn_skip.setProperty("class", "GhostButton")
        self.btn_skip.clicked.connect(self._finish)
        btn_row.addWidget(self.btn_skip)
        btn_row.addStretch()
        self.btn_next = QPushButton("Next")
        self.btn_next.setProperty("class", "PrimaryButton")
        self.btn_next.clicked.connect(self._advance)
        btn_row.addWidget(self.btn_next)
        card_layout.addLayout(btn_row)

        self.hide()

    # ------------------------------------------------------------------
    def start(self):
        self._index = 0
        self.setGeometry(self.host_rect())
        self.show()
        self.raise_()
        self._show_step()

    def host_rect(self):
        return self._host.rect()

    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj is self._host and self.isVisible():
            if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
                self.setGeometry(self.host_rect())
                self._show_step()
        return super().eventFilter(obj, event)

    def _current_target(self) -> QWidget | None:
        getter = self._steps[self._index].target
        widget = getter()
        if widget is not None and (not widget.isVisible() or widget.width() == 0):
            return None
        return widget

    def _show_step(self):
        step = self._steps[self._index]
        self.lbl_step.setText(f"Step {self._index + 1} of {len(self._steps)}")
        self.lbl_title.setText(step.title)
        self.lbl_body.setText(step.body)
        self.btn_next.setText("Done" if self._index == len(self._steps) - 1 else "Next")
        self._position_card()
        self.update()

    def _target_rect_on_host(self) -> QRectF | None:
        widget = self._current_target()
        if widget is None:
            return None
        global_pos = widget.mapTo(self._host, widget.rect().topLeft())
        return QRectF(global_pos.x() - 6, global_pos.y() - 6,
                      widget.width() + 12, widget.height() + 12)

    def _position_card(self):
        self.card.adjustSize()
        rect = self._target_rect_on_host()
        host = self.host_rect()
        cw, ch = self.card.width(), self.card.height()

        if rect is None:
            x = (host.width() - cw) // 2
            y = (host.height() - ch) // 2
        else:
            x = int(rect.right() + 16)
            y = int(rect.top())
            if x + cw > host.width() - 12:  # flip to left side
                x = int(rect.left() - cw - 16)
            if x < 12:
                x = 12
            if y + ch > host.height() - 12:
                y = host.height() - ch - 12
            if y < 12:
                y = 12
        self.card.move(max(x, 12), max(y, 12))
        self.card.raise_()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        outer = QPainterPath()
        outer.addRect(QRectF(self.rect()))

        rect = self._target_rect_on_host()
        if rect is not None:
            hole = QPainterPath()
            hole.addRoundedRect(rect, 12, 12)
            outer = outer.subtracted(hole)

        p.fillPath(outer, _DIM)

        if rect is not None:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(_ACCENT, 2))
            p.drawRoundedRect(rect, 12, 12)
        p.end()

    # ------------------------------------------------------------------
    def _advance(self):
        if self._index >= len(self._steps) - 1:
            self._finish()
        else:
            self._index += 1
            self._show_step()

    def _finish(self):
        self.hide()
        self.finished.emit()
