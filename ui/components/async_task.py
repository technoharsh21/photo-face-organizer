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
    the UI thread. Keep a reference to the instance until it finishes.
    """

    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, parent=None, **kwargs: Any):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001 - report every failure to UI
            traceback.print_exc()
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            self.result_ready.emit(result)
