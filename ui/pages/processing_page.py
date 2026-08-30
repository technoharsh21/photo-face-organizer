"""
Processing Screen Page Module.

Requirements #23, #24, #25:
Live scan monitoring UI with real-time counters, progress bar, processing speed, ETA,
and controls for Pause, Resume, and Cancel.
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from domain.worker import ScanWorker
from services.scan_service import ScanService


class ProcessingPage(QWidget):
    """Processing page showing live scan status and control buttons."""

    def __init__(
        self,
        scan_service: ScanService,
        on_scan_finished_cb: Callable[[dict[str, Any]], None],
    ):
        super().__init__()
        self.scan_service = scan_service
        self.on_scan_finished_cb = on_scan_finished_cb
        self.current_worker: ScanWorker | None = None

        self._setup_ui()

    def _setup_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(20, 20, 20, 20)
        page_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        content_widget = QWidget()
        content_widget.setMaximumWidth(880)
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        sub_title = QLabel("⚡ InsightFace SCRFD 360° face detection & ArcFace neural embedding in progress...")
        sub_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(sub_title)

        # Status & Progress Card
        card = QFrame()
        card.setProperty("class", "Card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        self.lbl_status = QLabel("Status: Processing...")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        card_layout.addWidget(self.lbl_status)

        self.lbl_file = QLabel("Current File: Initiating scan...")
        self.lbl_file.setStyleSheet("color: #cbd5e1; font-size: 13px; font-family: monospace;")
        card_layout.addWidget(self.lbl_file)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(24)
        card_layout.addWidget(self.progress_bar)

        self.lbl_speed_eta = QLabel("Speed: -- photos/sec | ETA: --")
        self.lbl_speed_eta.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        card_layout.addWidget(self.lbl_speed_eta)

        layout.addWidget(card)

        # Counters Grid
        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(12)

        self.c_processed = self._create_counter("Processed", "0", "#10b981")
        self.c_matched = self._create_counter("Matched", "0", "#8b5cf6")
        self.c_no_match = self._create_counter("No Match", "0", "#f59e0b")
        self.c_unknown = self._create_counter("Unknown Faces", "0", "#ec4899")
        self.c_skipped = self._create_counter("Skipped", "0", "#6b7280")
        self.c_errors = self._create_counter("Errors", "0", "#ef4444")

        stats_grid.addWidget(self.c_processed["frame"])
        stats_grid.addWidget(self.c_matched["frame"])
        stats_grid.addWidget(self.c_no_match["frame"])
        stats_grid.addWidget(self.c_unknown["frame"])
        stats_grid.addWidget(self.c_skipped["frame"])
        stats_grid.addWidget(self.c_errors["frame"])

        layout.addLayout(stats_grid)

        # Control Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)
        btn_layout.addStretch()

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setProperty("class", "SecondaryButton")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setFixedHeight(42)
        self.btn_pause.setStyleSheet(
            "QPushButton { background-color: #1e293b; color: #ffffff; font-weight: 700; border-radius: 8px; padding: 0 24px; font-size: 13px; min-height: 42px; max-height: 42px; border: 1px solid #3b82f6; }"
            "QPushButton:hover { background-color: #1d4ed8; color: #ffffff; }"
        )
        self.btn_pause.clicked.connect(self._toggle_pause)
        btn_layout.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("🛑 Cancel Scan")
        self.btn_cancel.setProperty("class", "DangerButton")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(42)
        self.btn_cancel.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: #ffffff; border: none; border-radius: 8px; padding: 0 24px; font-size: 13px; min-height: 42px; max-height: 42px; font-weight: 700; }"
            "QPushButton:hover { background-color: #b91c1c; }"
        )
        self.btn_cancel.clicked.connect(self._cancel_scan)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        page_layout.addWidget(content_widget)

    def _create_counter(self, title: str, val: str, color: str) -> dict:
        frame = QFrame()
        frame.setProperty("class", "Card")
        l = QVBoxLayout(frame)

        v_lbl = QLabel(val)
        v_lbl.setProperty("class", "StatValue")
        v_lbl.setStyleSheet(f"color: {color}; font-size: 24px;")
        t_lbl = QLabel(title)
        t_lbl.setProperty("class", "StatLabel")

        l.addWidget(v_lbl)
        l.addWidget(t_lbl)

        return {"frame": frame, "value": v_lbl}

    def start_monitoring(self, worker: ScanWorker):
        """Attach worker thread and connect progress signals."""
        self.current_worker = worker
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Status: Scanning & Processing...")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        self.btn_pause.setText("⏸ Pause")

        worker.progress_signal.connect(self._on_progress)
        worker.finished_signal.connect(self._on_finished)
        worker.start()

    def _on_progress(self, data: dict[str, Any]):
        file_name = data.get("current_file", "")
        progress = int(data.get("progress_percent", 0))
        processed = data.get("processed", 0)
        total = data.get("total_files", 0)

        self.lbl_file.setText(f"Processing ({processed}/{total}): {file_name}")
        self.progress_bar.setValue(progress)

        speed = data.get("speed_fps", 0)
        eta = data.get("eta_seconds", 0)
        self.lbl_speed_eta.setText(f"Speed: {speed} photos/sec | ETA: {int(eta)}s remaining")

        self.c_processed["value"].setText(str(processed))
        self.c_matched["value"].setText(str(data.get("matched", 0)))
        self.c_no_match["value"].setText(str(data.get("no_match", 0)))
        self.c_unknown["value"].setText(str(data.get("unknown_faces", 0)))
        self.c_skipped["value"].setText(str(data.get("skipped", 0)))
        self.c_errors["value"].setText(str(data.get("errors", 0)))

    def _toggle_pause(self):
        if not self.current_worker:
            return
        from PySide6.QtWidgets import QApplication

        if self.current_worker.is_paused:
            self.current_worker.resume()
            self.btn_pause.setText("⏸ Pause")
            self.lbl_status.setText("Status: Scanning & Processing...")
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        else:
            self.current_worker.pause()
            self.btn_pause.setText("▶ Resume")
            self.lbl_status.setText("Status: PAUSED")
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #f59e0b;")

        QApplication.processEvents()

    def _cancel_scan(self):
        if not self.current_worker:
            return
        from PySide6.QtWidgets import QApplication

        res = QMessageBox.question(
            self, "Confirm Cancel", "Are you sure you want to cancel the scan?", QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            self.current_worker.cancel()
            self.lbl_status.setText("Status: CANCELLED")
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #ef4444;")
            QApplication.processEvents()

    def _on_finished(self, summary: dict[str, Any]):
        self.current_worker = None
        self.on_scan_finished_cb(summary)
