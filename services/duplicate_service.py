"""
Duplicate Service Module.

Scans directories for duplicate images using fast size pre-filtering and SHA-256 content hashing.
Provides smart auto-selection rules (Keep Oldest, Keep Newest, Keep Shortest Path)
and safe cleanup options (OS Trash / Recycle Bin or Permanent Delete).
"""

import datetime
import hashlib
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

from config import Config
from domain.file_utils import send_to_trash
from domain.scanner import discover_photos

logger = logging.getLogger(__name__)

# Regex pattern detecting copy indicators like " - Copy", " (1)", "_copy", "_1", " (2)", etc.
COPY_NAME_PATTERN = re.compile(
    r'(?:[-_\s]+copy(?:\s*\(\d+\))?|\s*\(\d+\)|[-_]\d+|[-_]duplicate)',
    re.IGNORECASE
)


def is_copy_filename(filename: str) -> bool:
    """Check whether a filename looks like an OS-generated copy or duplicate name."""
    stem = Path(filename).stem
    return bool(COPY_NAME_PATTERN.search(stem))


def format_bytes(size_bytes: int) -> str:
    """Format byte count into human-readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _is_relative_to_compat(child: Path, parent: Path) -> bool:
    """Path.is_relative_to() requires Python 3.9+; use relative_to() try/except instead."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


class DuplicateService:
    """Service for detecting, grouping, auto-selecting, and removing duplicate image files."""

    def __init__(self, config: Config):
        self.config = config

    @staticmethod
    def compute_file_hash(file_path: Path, block_size: int = 65536) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def scan_directories_for_duplicates(
        self, sources: list[str | Path], recursive: bool = True
    ) -> list[dict[str, Any]]:
        """
        Scans directories for duplicate images.
        Step 1: Discover all image files.
        Step 2: Group by file size (instant filter).
        Step 3: For sizes with 2+ files, compute SHA-256 hash.
        Step 4: Group by hash and return list of duplicate sets.
        """
        resolved_sources = [Path(s).resolve() for s in sources if s]
        photo_paths = discover_photos(sources, recursive=recursive)
        if not photo_paths:
            return []

        # Filter photo paths to guarantee strict path isolation within target sources
        valid_paths = []
        for p in photo_paths:
            p_res = p.resolve()
            if recursive:
                if any(_is_relative_to_compat(p_res, src) for src in resolved_sources):
                    valid_paths.append(p_res)
            else:
                if any(p_res.parent == src or p_res == src for src in resolved_sources):
                    valid_paths.append(p_res)

        if not valid_paths:
            return []

        # Step 1: Group by file size
        size_groups: dict[int, list[Path]] = {}
        for p in valid_paths:
            try:
                st = p.stat()
                if st.st_size > 0:
                    size_groups.setdefault(st.st_size, []).append(p)
            except Exception:
                pass

        # Candidate sizes with 2 or more files
        candidate_paths: list[Path] = []
        for size, files in size_groups.items():
            if len(files) >= 2:
                candidate_paths.extend(files)

        if not candidate_paths:
            return []

        # Step 2: Compute SHA-256 hash for candidates
        hash_groups: dict[str, list[Path]] = {}
        for p in candidate_paths:
            try:
                f_hash = self.compute_file_hash(p)
                hash_groups.setdefault(f_hash, []).append(p)
            except Exception as e:
                logger.warning(f"Could not hash file {p}: {e}")

        # Step 3: Build duplicate sets for hashes with >= 2 files
        duplicate_sets: list[dict[str, Any]] = []
        set_idx = 1

        for f_hash, files in hash_groups.items():
            if len(files) >= 2:
                file_items = []
                for p in files:
                    try:
                        st = p.stat()
                        mtime_iso = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        ctime = getattr(st, "st_birthtime", None) or getattr(st, "st_ctime", st.st_mtime)
                        file_items.append({
                            "path": str(p),
                            "filename": p.name,
                            "size": st.st_size,
                            "formatted_size": format_bytes(st.st_size),
                            "mtime": st.st_mtime,
                            "ctime": ctime,
                            "formatted_mtime": mtime_iso,
                            "is_recommended_keep": False,
                            "is_selected_for_removal": False,
                        })
                    except Exception:
                        pass

                if len(file_items) >= 2:
                    sample_name = file_items[0]["filename"]
                    single_size = file_items[0]["size"]
                    potential_savings = single_size * (len(file_items) - 1)

                    duplicate_sets.append({
                        "set_id": f"set_{set_idx}",
                        "hash": f_hash,
                        "sample_name": sample_name,
                        "file_count": len(file_items),
                        "single_size": single_size,
                        "potential_savings": potential_savings,
                        "formatted_savings": format_bytes(potential_savings),
                        "files": file_items,
                    })
                    set_idx += 1

        self.apply_auto_select_rule(duplicate_sets, rule="keep_oldest")
        return duplicate_sets

    def apply_auto_select_rule(
        self, duplicate_sets: list[dict[str, Any]], rule: str = "keep_oldest"
    ):
        """
        Applies auto-selection rule across all duplicate sets:
        - 'keep_oldest': Keeps original photo with earliest timestamp, prioritizing non-copy filenames.
        - 'keep_newest': Keeps most recently created or modified duplicate copy.
        - 'keep_shortest_path': Keeps file with shortest and cleanest file path.
        """
        for dset in duplicate_sets:
            files = dset.get("files", [])
            if not files:
                continue

            # Reset flags
            for f in files:
                f["is_recommended_keep"] = False
                f["is_selected_for_removal"] = False

            if rule == "keep_oldest":
                def _key_oldest(x):
                    is_copy = 1 if is_copy_filename(x.get("filename", "")) else 0
                    mtime = x.get("mtime", 0.0)
                    ctime = x.get("ctime", mtime)
                    filename = x.get("filename", "")
                    path = x.get("path", "")
                    # Priority: Earliest mtime -> Earliest ctime -> Original clean name -> Shorter filename -> Shorter path
                    return (mtime, ctime, is_copy, len(filename), len(path), path)

                files.sort(key=_key_oldest)

            elif rule == "keep_newest":
                def _key_newest(x):
                    is_copy = 1 if is_copy_filename(x.get("filename", "")) else 0
                    mtime = x.get("mtime", 0.0)
                    ctime = x.get("ctime", mtime)
                    filename = x.get("filename", "")
                    path = x.get("path", "")
                    return (-mtime, -ctime, -is_copy, -len(filename), -len(path), path)

                files.sort(key=_key_newest)

            elif rule == "keep_shortest_path":
                def _key_shortest(x):
                    is_copy = 1 if is_copy_filename(x.get("filename", "")) else 0
                    path = x.get("path", "")
                    filename = x.get("filename", "")
                    mtime = x.get("mtime", 0.0)
                    return (len(path), is_copy, len(filename), mtime, path)

                files.sort(key=_key_shortest)

            else:
                files.sort(key=lambda x: x.get("mtime", 0.0))

            # Keep the first file according to rule
            files[0]["is_recommended_keep"] = True
            for f in files[1:]:
                f["is_selected_for_removal"] = True

            dset["sample_name"] = files[0]["filename"]

    def remove_duplicates(
        self,
        file_paths_to_remove: list[str],
        mode: str = "trash",
        progress_cb: Any = None,
        cancel_check: Any = None,
    ) -> tuple[int, int, int]:
        """
        Removes selected duplicate files by moving them to OS Trash / Recycle Bin or permanently deleting them.
        Modes:
        - 'trash': Sends files to OS Trash / Recycle Bin.
        - 'delete': Permanently unlinks files.

        Returns: (success_count, error_count, freed_bytes)
        """
        success_count = 0
        error_count = 0
        freed_bytes = 0
        total = len(file_paths_to_remove)

        for idx, p_str in enumerate(file_paths_to_remove):
            if cancel_check and cancel_check():
                break

            if progress_cb:
                progress_cb(idx + 1, total, Path(p_str).name)

            p = Path(p_str)
            if not p.exists():
                continue

            try:
                f_size = p.stat().st_size
                if mode == "trash":
                    trashed = send_to_trash(p)
                    if not trashed:
                        logger.error(f"Failed to send duplicate file {p_str} to trash.")
                        error_count += 1
                        continue
                elif mode == "delete":
                    p.unlink()

                success_count += 1
                freed_bytes += f_size
            except Exception as e:
                logger.error(f"Failed to remove duplicate file {p_str}: {e}")
                error_count += 1

        return success_count, error_count, freed_bytes
