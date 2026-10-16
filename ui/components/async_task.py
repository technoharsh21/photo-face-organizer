"""
Async Task Helper.

Reusable QThread wrapper that runs a blocking callable off the GUI event loop
and delivers its result (or exception) back to the UI thread via Qt signals.
"""

import traceback
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class AsyncTask(QThread):
    """Runs ``fn(*args, **kwargs)`` in a background thread.

    Emit ``result_ready(result)`` on success or ``failed(error_string)`` on
    the UI thread. Retains a reference to running tasks to guarantee the thread
    is never destroyed prematurely by garbage collection.
    """

    result_ready = Signal(object)
    failed = Signal(str)

    _running_tasks: set["AsyncTask"] = set()

    def __init__(self, fn: Callable[..., Any], *args: Any, parent=None, **kwargs: Any):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.finished.connect(self._on_finished)

    def start(self, priority=QThread.Priority.InheritPriority):
        AsyncTask._running_tasks.add(self)
        super().start(priority)

    def _on_finished(self):
        AsyncTask._running_tasks.discard(self)

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 - report every failure to UI
            traceback.print_exc()
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.result_ready.emit(result)
