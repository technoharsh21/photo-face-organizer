"""
File Utility Module for Safe File Deletions and Trashing.

Provides cross-platform support for sending files to the OS Recycle Bin / Trash,
with multi-tier fallbacks (send2trash, Linux gio/trash-put, macOS AppleScript, Windows PowerShell).
"""

import logging
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_copy_pairs(pairs: list[tuple[str, str]]) -> tuple[bool, int, list[str], dict[str, tuple[str, list[str]]]]:
    """Verify actual bytes for every output before offering to remove any source."""
    verified: dict[str, tuple[str, list[str]]] = {}
    for source, target in pairs:
        try:
            src, dst = Path(source), Path(target)
            if src.resolve() == dst.resolve() or not src.is_file() or not dst.is_file() or not src.stat().st_size:
                raise ValueError("Missing, empty, or overlapping source/destination")
            source_hash = _file_hash(src)
            if source_hash != _file_hash(dst):
                raise ValueError("Copy content does not match source")
            if source in verified and verified[source][0] != source_hash:
                raise ValueError("Source changed during verification")
            verified.setdefault(source, (source_hash, []))[1].append(target)
        except (OSError, ValueError) as exc:
            logger.warning("Copy verification failed for %s -> %s: %s", source, target, exc)
            return False, 0, [], {}
    return True, len(verified), list(verified), verified


def trash_verified_sources(source_paths: list[str], verified: dict[str, tuple[str, list[str]]]) -> tuple[int, int]:
    """Recheck every copy before trashing; never delete permanently on Trash failure."""
    deleted = errors = 0
    for source in source_paths:
        record = verified.pop(source, None)
        try:
            if not record or not record[1] or _file_hash(Path(source)) != record[0] or any(
                Path(source).resolve() == Path(target).resolve() or _file_hash(Path(target)) != record[0]
                for target in record[1]
            ):
                raise ValueError("Unverified or changed source/copy")
            if not send_to_trash(Path(source)):
                raise OSError("Could not move source to Trash")
            deleted += 1
        except (OSError, ValueError) as exc:
            logger.warning("Keeping source %s: %s", source, exc)
            errors += 1
    return deleted, errors


def _win32_recycle_bin(path_str: str) -> bool:
    """
    Direct in-process Windows Shell API call to move file to Recycle Bin.
    Uses SHFileOperationW from shell32.dll with FOF_ALLOWUNDO (no console window, instant <1ms).
    """
    try:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_uint16),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 0x0003
        FOF_ALLOWUNDO = 0x0040        # Move to Recycle Bin instead of permanent delete
        FOF_NOCONFIRMATION = 0x0010   # Don't ask user confirmation
        FOF_SILENT = 0x0004           # Don't show Windows progress dialog
        FOF_NOERRORUI = 0x0400        # Don't show error dialog

        flags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        p_from = path_str + "\0\0"

        fileop = SHFILEOPSTRUCTW(
            hwnd=None,
            wFunc=FO_DELETE,
            pFrom=p_from,
            pTo=None,
            fFlags=flags,
            fAnyOperationsAborted=False,
            hNameMappings=None,
            lpszProgressTitle=None,
        )

        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        return res == 0 and not fileop.fAnyOperationsAborted
    except Exception as e:
        logger.debug(f"Win32 SHFileOperationW failed: {e}")
        return False


def send_to_trash(file_path: str | Path) -> bool:
    """
    Sends a file to the OS Recycle Bin / Trash in a cross-platform manner.

    Tries the following methods in order:
    1. send2trash (cross-platform Python library)
    2. Platform-native commands / APIs:
       - Linux: gio trash, trash-put
       - macOS: AppleScript (Finder delete)
       - Windows: Win32 SHFileOperationW (in-process, 0ms, no window), PowerShell fallback (hidden window)
    
    Returns:
        bool: True if the file was successfully moved to Trash / Recycle Bin, False otherwise.
    """
    p = Path(file_path).resolve()
    if not p.exists():
        logger.warning(f"File not found for trashing: {p}")
        return False

    str_path = str(p)

    # 1. Try send2trash library
    try:
        import send2trash
        send2trash.send2trash(str_path)
        if not p.exists():
            logger.info(f"Successfully sent to trash via send2trash: {str_path}")
            return True
    except Exception as e:
        logger.debug(f"send2trash failed for {str_path}: {e}")

    # 2. Platform-specific fallbacks
    if sys.platform.startswith("linux"):
        # Linux: try gio trash
        if shutil.which("gio"):
            try:
                res = subprocess.run(
                    ["gio", "trash", str_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0 and not p.exists():
                    logger.info(f"Successfully sent to trash via gio: {str_path}")
                    return True
                else:
                    logger.debug(f"gio trash returned {res.returncode}: {res.stderr}")
            except Exception as e:
                logger.debug(f"gio trash execution failed: {e}")

        # Linux: try trash-put (trash-cli)
        if shutil.which("trash-put"):
            try:
                res = subprocess.run(
                    ["trash-put", str_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0 and not p.exists():
                    logger.info(f"Successfully sent to trash via trash-put: {str_path}")
                    return True
            except Exception as e:
                logger.debug(f"trash-put execution failed: {e}")

    elif sys.platform == "darwin":
        # macOS: try AppleScript Finder delete
        try:
            script = f'tell application "Finder" to delete POSIX file "{str_path}"'
            res = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and not p.exists():
                logger.info(f"Successfully sent to trash via AppleScript: {str_path}")
                return True
        except Exception as e:
            logger.debug(f"osascript trash failed: {e}")

    elif sys.platform == "win32":
        # Windows: Try native in-process Win32 Shell API (Instant, No console window)
        try:
            if _win32_recycle_bin(str_path) and not p.exists():
                logger.info(f"Successfully sent to recycle bin via Win32 Shell API: {str_path}")
                return True
        except Exception as e:
            logger.debug(f"Win32 Shell API failed for {str_path}: {e}")

    logger.error(f"All trash methods failed for file: {str_path}")
    return False
