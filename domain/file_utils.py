"""
File Utility Module for Safe File Deletions and Trashing.

Provides cross-platform support for sending files to the OS Recycle Bin / Trash,
with multi-tier fallbacks (send2trash, Linux gio/trash-put, macOS AppleScript, Windows PowerShell).
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


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
        # Windows 1: Try native in-process Win32 Shell API (Instant, No console window)
        try:
            if _win32_recycle_bin(str_path) and not p.exists():
                logger.info(f"Successfully sent to recycle bin via Win32 Shell API: {str_path}")
                return True
        except Exception as e:
            logger.debug(f"Win32 Shell API failed for {str_path}: {e}")

        # Windows 2: Try PowerShell FileSystem.DeleteFile with hidden window flags
        try:
            ps_cmd = (
                f"Add-Type -AssemblyName Microsoft.VisualBasic; "
                f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{str_path}', "
                f"'OnlyErrorDialogs', 'SendToRecycleBin')"
            )
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                check=False,
                creationflags=creation_flags,
            )
            if res.returncode == 0 and not p.exists():
                logger.info(f"Successfully sent to recycle bin via PowerShell: {str_path}")
                return True
        except Exception as e:
            logger.debug(f"PowerShell recycle bin failed: {e}")

    logger.error(f"All trash methods failed for file: {str_path}")
    return False
