"""
Photo Face Organizer Application Entry Point.

Initializes application services, face recognition engine, configuration,
logging to file/console, crash error hooks, and PySide6 QApplication main loop.
Disables bytecode caching (pycache) in dev mode.
"""

import datetime
import io
import logging
import os
import platform
import sys
import threading
import traceback
from pathlib import Path

# PyInstaller --windowed mode sets sys.stdout/stderr to None on Windows.
# InsightFace/ONNX internally call print() which crashes with 'NoneType' has no attribute 'write'.
# Fix: replace None streams with real OS-level /dev/null file handles BEFORE any library imports.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Disable Python bytecode (.pyc) caching to guarantee fresh code is loaded on every launch
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# Show the OS-native file / folder selection dialog on Linux. Without a platform
# theme, Qt falls back to its own built-in (non-native) QFileDialog. The gtk3 and
# xdgdesktopportal theme plugins ship inside the PySide6 wheel; the env var must be
# set before QApplication is created.
if sys.platform.startswith("linux") and not os.environ.get("QT_QPA_PLATFORMTHEME"):
    os.environ["QT_QPA_PLATFORMTHEME"] = (
        "xdgdesktopportal" if "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper() else "gtk3"
    )


def _clean_pycache():
    """Remove cached __pycache__ folders and .pyc files on launch."""
    root = Path(__file__).parent
    for p in root.rglob("*.pyc"):
        try:
            p.unlink()
        except Exception:
            pass


if not getattr(sys, "frozen", False):
    _clean_pycache()

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from config import Config
import faulthandler
from domain.duplicate_detector import DuplicateDetector
from domain.insight_engine import InsightFaceEngine
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.scan_service import ScanService
from services.settings_service import SettingsService
from services.unknown_face_service import UnknownFaceService
from ui.main_window import MainWindow
from ui.styles import get_dark_palette, get_stylesheet


class AutoFlushFileHandler(logging.FileHandler):
    """FileHandler that flushes on every write so logs are never lost on process abort."""

    def emit(self, record):
        super().emit(record)
        self.flush()


def _collect_system_info() -> str:
    """
    Collect detailed system, environment, and runtime information for crash reports.
    Gathers Python version, OS details, installed packages, GPU info, Qt version,
    memory stats, and relevant environment variables. Never raises — all errors are caught.
    """
    lines: list[str] = []

    def safe(label: str, fn):
        try:
            lines.append(f"  {label}: {fn()}")
        except Exception as exc:
            lines.append(f"  {label}: <error: {exc}>")

    # ── Timestamp & Runtime ────────────────────────────────────────────────────
    lines.append("[ RUNTIME ]")
    safe("Timestamp (UTC)",  lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    safe("Timestamp (Local)", lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    safe("Python",           lambda: sys.version.replace("\n", " "))
    safe("Executable",       lambda: sys.executable)
    safe("Frozen (PyInstaller)", lambda: str(getattr(sys, "frozen", False)))
    safe("Working Dir",      lambda: os.getcwd())
    safe("App Dir",          lambda: str(Path(__file__).resolve().parent))
    safe("Active Threads",   lambda: str(threading.active_count()))

    # ── Operating System ───────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ OPERATING SYSTEM ]")
    safe("Platform",         lambda: sys.platform)
    safe("OS",               lambda: platform.platform())
    safe("OS Version",       lambda: platform.version())
    safe("Architecture",     lambda: platform.machine())
    safe("Processor",        lambda: platform.processor() or platform.machine())
    safe("Node",             lambda: platform.node())

    # ── Memory ─────────────────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ MEMORY ]")
    try:
        import psutil
        vm = psutil.virtual_memory()
        safe("RAM Total",    lambda: f"{vm.total / 1024**3:.2f} GB")
        safe("RAM Available", lambda: f"{vm.available / 1024**3:.2f} GB")
        safe("RAM Used %",   lambda: f"{vm.percent}%")
        try:
            proc = psutil.Process(os.getpid())
            safe("Process RSS", lambda: f"{proc.memory_info().rss / 1024**2:.1f} MB")
        except Exception:
            pass
    except ImportError:
        lines.append("  psutil not installed — memory stats unavailable")

    # ── Qt / PySide6 ──────────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ QT / PYSIDE6 ]")
    try:
        from PySide6.QtCore import __version__ as pyside_ver, qVersion
        safe("PySide6 Version",  lambda: pyside_ver)
        safe("Qt Runtime",       lambda: qVersion())
    except Exception as e:
        lines.append(f"  PySide6 info unavailable: {e}")

    # ── AI / ONNX Runtime ─────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ AI ENGINE ]")
    try:
        import onnxruntime as ort
        safe("ONNX Runtime",     lambda: ort.__version__)
        safe("Execution Providers", lambda: str(ort.get_available_providers()))
    except ImportError:
        lines.append("  onnxruntime not installed")
    except Exception as e:
        lines.append(f"  ONNX info error: {e}")

    try:
        import insightface
        safe("InsightFace",      lambda: getattr(insightface, "__version__", "installed"))
    except ImportError:
        lines.append("  insightface not installed")

    try:
        import numpy as np
        safe("NumPy",            lambda: np.__version__)
    except ImportError:
        lines.append("  numpy not installed")

    try:
        import cv2
        safe("OpenCV",           lambda: cv2.__version__)
    except ImportError:
        lines.append("  opencv-python not installed")

    # ── GPU Info ──────────────────────────────────────────────────────────────
    lines.append("")
    lines.append("[ GPU ]")
    try:
        import subprocess
        if sys.platform == "win32":
            out = subprocess.check_output(
                "wmic path win32_VideoController get name,AdapterRAM /format:csv",
                shell=True, text=True, stderr=subprocess.DEVNULL, timeout=5
            )
            gpu_lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
            for gl in gpu_lines[:3]:
                parts = gl.split(",")
                if len(parts) >= 3:
                    try:
                        vram_mb = int(parts[1]) // (1024 ** 2) if parts[1].strip().isdigit() else 0
                        lines.append(f"  GPU: {parts[2].strip()} (VRAM: {vram_mb} MB)" if vram_mb else f"  GPU: {parts[2].strip()}")
                    except Exception:
                        lines.append(f"  GPU: {gl}")
        elif sys.platform.startswith("linux"):
            for cmd in (["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                        ["rocm-smi", "--showproductname"]):
                try:
                    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=5)
                    lines.append(f"  {out.strip()[:120]}")
                    break
                except Exception:
                    continue
            else:
                lines.append("  GPU: No NVIDIA/AMD CLI found (check lspci for GPU details)")
    except Exception as e:
        lines.append(f"  GPU detection error: {e}")

    # ── Relevant Environment Variables ────────────────────────────────────────
    lines.append("")
    lines.append("[ ENVIRONMENT ]")
    relevant_env = [
        "CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "QT_QPA_PLATFORM", "QT_QPA_PLATFORMTHEME", "DISPLAY", "WAYLAND_DISPLAY",
        "XDG_CURRENT_DESKTOP", "LOCALAPPDATA", "APPDATA",
        "PYTHONDONTWRITEBYTECODE", "VIRTUAL_ENV",
    ]
    for var in relevant_env:
        val = os.environ.get(var)
        if val:
            lines.append(f"  {var}={val}")

    return "\n".join(lines)


def _format_crash_report(
    exc_type: type,
    exc_value: BaseException,
    exc_traceback,
    crash_file: Path,
    session_start: datetime.datetime,
) -> str:
    """
    Build a rich, structured crash report string that is easy to read and action.
    Sections: header banner, error details, full traceback, exception chain,
    system snapshot, log file location, and next-steps hint for the developer.
    """
    sep  = "=" * 72
    dash = "-" * 72
    now  = datetime.datetime.now()
    uptime = now - session_start

    # ── Full traceback (with chained causes) ─────────────────────────────────
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    full_tb  = "".join(tb_lines).rstrip()
    if not full_tb:
        full_tb = f"{exc_type.__name__}: {exc_value}\n(no Python traceback was captured — likely raised from a C extension)"

    # ── Inner exception chain ─────────────────────────────────────────────────
    chain_parts: list[str] = []
    cause = getattr(exc_value, "__cause__", None) or getattr(exc_value, "__context__", None)
    depth = 0
    while cause and depth < 5:
        chain_parts.append(
            f"  {'Caused by' if getattr(exc_value, '__cause__', None) else 'During handling of'} "
            f"{type(cause).__name__}: {cause}"
        )
        cause = getattr(cause, "__cause__", None) or getattr(cause, "__context__", None)
        depth += 1

    # ── Local variables from innermost frame ──────────────────────────────────
    local_vars_str = ""
    try:
        tb = exc_traceback
        while tb.tb_next:
            tb = tb.tb_next
        frame_locals = tb.tb_frame.f_locals
        # Summarize locals — truncate large values (arrays, dicts)
        local_lines = []
        for k, v in list(frame_locals.items())[:20]:
            try:
                rep = repr(v)
                rep = rep[:200] + "…" if len(rep) > 200 else rep
            except Exception:
                rep = "<unrepresentable>"
            local_lines.append(f"    {k} = {rep}")
        local_vars_str = "\n".join(local_lines) if local_lines else "    (none)"
    except Exception:
        local_vars_str = "    (could not capture local variables)"

    # ── System info snapshot ──────────────────────────────────────────────────
    sys_info = _collect_system_info()

    # ── Assemble report ───────────────────────────────────────────────────────
    report = f"""
{sep}
  PHOTO FACE ORGANIZER — CRASH REPORT
  Crashed At : {now.strftime("%Y-%m-%d %H:%M:%S")} (local)
  Session Up : {str(uptime).split(".")[0]} (hh:mm:ss)
  Crash File : {crash_file}
  Platform   : {sys.platform} | Python {sys.version.split()[0]}
{sep}

{dash}
  EXCEPTION SUMMARY
{dash}
  Type    : {exc_type.__module__}.{exc_type.__qualname__}
  Message : {exc_value}
  Repr    : {repr(exc_value)[:300]}
"""

    if chain_parts:
        report += "\n" + "\n".join(chain_parts) + "\n"

    report += f"""
{dash}
  FULL TRACEBACK
{dash}
{full_tb}

{dash}
  LOCAL VARIABLES (innermost frame at time of crash)
{dash}
{local_vars_str}

{dash}
  SYSTEM SNAPSHOT
{dash}
{sys_info}

{dash}
  HOW TO DIAGNOSE THIS CRASH
{dash}
  1. Read the FULL TRACEBACK above — the last "File ..." line is where it crashed.
  2. Check LOCAL VARIABLES for unexpected None / NaN / empty values.
  3. Check the SYSTEM SNAPSHOT — GPU/VRAM/RAM issues often cause AI inference crashes.
  4. If the exception type is OverflowError → bbox contains NaN/Inf from ONNX.
  5. If the exception type is RuntimeError / OSError → check GPU driver / ONNX provider.
  6. If no traceback was captured → a C extension (ONNX / OpenCV / Qt) crashed natively.
     Enable faulthandler output (see crash_log.txt) for the native stack dump.
  7. Full application log: {crash_file.parent / "photo_face_organizer.log"}

{sep}
"""
    return report


def _setup_crash_logging(config: Config):
    """
    Set up persistent auto-flush file logging, native faulthandler for C++ crashes,
    and a rich Python uncaught-exception hook that writes detailed crash reports.
    """
    log_file   = config.app_data_dir / "photo_face_organizer.log"
    crash_file = config.app_data_dir / "crash_log.txt"

    # Track session start time for uptime calculation in crash reports
    session_start = datetime.datetime.now()

    try:
        config.app_data_dir.mkdir(parents=True, exist_ok=True)

        # ── File handler (auto-flush so logs survive hard crashes) ────────────
        file_handler = AutoFlushFileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-8s] (%(threadName)s) %(name)s: %(message)s"
        ))

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)   # Capture DEBUG+ to file; UI shows INFO+
        root_logger.addHandler(file_handler)

        # ── Console handler (INFO+ only, avoids spamming debug noise) ─────────
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            "[%(levelname)s] %(name)s: %(message)s"
        ))
        root_logger.addHandler(console_handler)

        # ── Native faulthandler — catches SIGSEGV, D3D12 device-lost, etc. ───
        try:
            fault_fp = open(crash_file, "a", encoding="utf-8")
            faulthandler.enable(file=fault_fp, all_threads=True)
            logging.debug("faulthandler enabled → native crash stacks will appear in crash_log.txt")
        except Exception as f_err:
            logging.warning(f"Could not enable faulthandler: {f_err}")

        # ── Startup banner ────────────────────────────────────────────────────
        sep = "=" * 60
        logging.info(sep)
        logging.info("Photo Face Organizer  —  Session Started")
        logging.info(f"  Time      : {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"  Python    : {sys.version.split()[0]}  |  Platform: {sys.platform}")
        logging.info(f"  Executable: {sys.executable}")
        logging.info(f"  Log file  : {log_file}")
        logging.info(f"  Crash log : {crash_file}")
        logging.info(sep)

    except Exception as e:
        print(f"[FATAL] Failed to initialize crash logging: {e}", file=sys.stderr)

    # ── Rich uncaught-exception hook ──────────────────────────────────────────
    def uncaught_exception_hook(exc_type, exc_value, exc_traceback):
        # Let Ctrl-C pass through normally
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        report = _format_crash_report(
            exc_type, exc_value, exc_traceback,
            crash_file=crash_file,
            session_start=session_start,
        )

        # 1. Write to structured application log
        logging.critical(report)

        # 2. Write to dedicated crash_log.txt (always, even if logger is broken)
        try:
            with open(crash_file, "a", encoding="utf-8") as f:
                f.write(report)
        except Exception:
            pass

        # 3. Show user-facing error dialog with summary + copyable full report
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance():
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle("Photo Face Organizer — Unexpected Error")
                msg_box.setText(
                    f"<b>The application encountered an unexpected error.</b><br><br>"
                    f"<code>{exc_type.__name__}: {exc_value}</code>"
                )
                msg_box.setInformativeText(
                    f"A detailed crash report has been saved to:<br>"
                    f"<code>{crash_file}</code><br><br>"
                    f"Click <b>Show Details</b> to view the full report, or open the file above."
                )
                msg_box.setDetailedText(report)
                msg_box.exec()
        except Exception:
            pass

    sys.excepthook = uncaught_exception_hook



from PySide6.QtNetwork import QLocalServer, QLocalSocket
from services.face_cache_service import FaceCacheService
from services.solo_scan_service import SoloScanService

SINGLE_INSTANCE_KEY = "PhotoFaceOrganizer_SingleInstance_AppKey"


def ensure_single_instance() -> tuple[bool, QLocalServer | None]:
    """
    Ensures only a single instance of Photo Face Organizer runs concurrently.
    If an existing instance is found, sends an 'ACTIVATE' message to bring it to focus,
    and returns (False, None).
    If no instance is running, starts a QLocalServer to listen and returns (True, server).
    """
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_KEY)
    if socket.waitForConnected(500):
        # Existing instance running -> send message to wake it up and exit
        try:
            socket.write(b"ACTIVATE\n")
            socket.waitForBytesWritten(500)
        except Exception:
            pass
        finally:
            socket.disconnectFromServer()
        return False, None

    # First instance -> Start listening
    server = QLocalServer()
    # Remove any stale lock file from previous crash
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
    if not server.listen(SINGLE_INSTANCE_KEY):
        QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        server.listen(SINGLE_INSTANCE_KEY)

    return True, server


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Photo Face Organizer")
    app.setDesktopFileName("photofaceorganizer")

    # Single-instance enforcement: prevent duplicate running windows
    is_first, single_instance_server = ensure_single_instance()
    if not is_first:
        sys.exit(0)

    app.setStyleSheet(get_stylesheet())
    app.setPalette(get_dark_palette())

    # Set application icon (PNG / ICO fallback)
    root_dir = Path(__file__).resolve().parent
    icon_path = root_dir / "icon.png"
    if not icon_path.exists():
        icon_path = root_dir / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    config = Config()
    _setup_crash_logging(config)

    settings_service = SettingsService(config)
    face_cache_service = FaceCacheService(config, settings_service)

    device_pref = settings_service.get("device_preference", "Auto")
    from domain.insight_engine import InsightFaceEngine
    face_engine = InsightFaceEngine(device_preference=device_pref)

    duplicate_detector = DuplicateDetector(config.duplicate_index_file)
    output_service = OutputService(duplicate_detector)

    profile_service = ProfileService(config, face_engine)
    unknown_face_service = UnknownFaceService(config, profile_service)
    history_service = HistoryService(config)

    scan_service = ScanService(
        config=config,
        face_engine=face_engine,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        profile_service=profile_service,
    )

    solo_scan_service = SoloScanService(
        config=config,
        face_engine=face_engine,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        profile_service=profile_service,
        face_cache_service=face_cache_service,
    )

    main_window = MainWindow(
        config=config,
        face_engine=face_engine,
        profile_service=profile_service,
        scan_service=scan_service,
        solo_scan_service=solo_scan_service,
        output_service=output_service,
        unknown_face_service=unknown_face_service,
        history_service=history_service,
        settings_service=settings_service,
        face_cache_service=face_cache_service,
    )

    # Wire up single-instance activation listener
    if single_instance_server:
        def _on_new_instance():
            conn = single_instance_server.nextPendingConnection()
            if conn:
                def _activate():
                    try:
                        conn.readAll()
                    except Exception:
                        pass
                    if main_window.isMinimized():
                        main_window.showNormal()
                    main_window.show()
                    main_window.raise_()
                    main_window.activateWindow()

                conn.readyRead.connect(_activate)

        single_instance_server.newConnection.connect(_on_new_instance)

    main_window.show()
    app.aboutToQuit.connect(settings_service.flush)
    sys.exit(app.exec())


import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
