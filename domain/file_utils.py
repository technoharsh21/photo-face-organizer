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


def send_to_trash(file_path: str | Path) -> bool:
    """
    Sends a file to the OS Recycle Bin / Trash in a cross-platform manner.

    Tries the following methods in order:
    1. send2trash (cross-platform Python library)
    2. Platform-native commands:
       - Linux: gio trash, trash-put
       - macOS: AppleScript (Finder delete)
       - Windows: PowerShell Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile
    
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
        # Windows: try PowerShell FileSystem.DeleteFile with SendToRecycleBin
        try:
            ps_cmd = (
                f"Add-Type -AssemblyName Microsoft.VisualBasic; "
                f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{str_path}', "
                f"'OnlyErrorDialogs', 'SendToRecycleBin')"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and not p.exists():
                logger.info(f"Successfully sent to recycle bin via PowerShell: {str_path}")
                return True
        except Exception as e:
            logger.debug(f"PowerShell recycle bin failed: {e}")

    logger.error(f"All trash methods failed for file: {str_path}")
    return False
