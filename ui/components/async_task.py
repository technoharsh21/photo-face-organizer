"""
Async Task Helper.

Reusable QThread wrapper that runs a blocking callable off the GUI event loop
and delivers its result (or exception) back to the UI thread via Qt signals.
"""

import logging
import traceback
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


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
        fn_name = getattr(self._fn, "__qualname__", None) or getattr(self._fn, "__name__", repr(self._fn))
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:
            tb_str = traceback.format_exc()
            # Log full traceback to file so it appears in photo_face_organizer.log
            logger.error(
                f"AsyncTask FAILED  |  fn={fn_name}\n"
                f"  Exception : {type(exc).__name__}: {exc}\n"
                f"  Traceback :\n{tb_str}"
            )
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        else:
            result_repr = repr(result)
            if len(result_repr) > 120:
                result_repr = result_repr[:120] + "…"
            logger.debug(f"AsyncTask OK  |  fn={fn_name}  |  result={result_repr}")
            self.result_ready.emit(result)
