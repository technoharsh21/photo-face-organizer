"""
Duplicate Service Module.

Scans directories for duplicate images using fast size pre-filtering and SHA-256 content hashing,
as well as perceptual hashing (pHash/dHash) to detect mobile copies, recompressed JPEGs, and photos
with modified EXIF metadata.
Provides smart auto-selection rules (Keep Oldest, Keep Newest, Keep Shortest Path)
and safe cleanup options (OS Trash / Recycle Bin or Permanent Delete).
"""

from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from config import Config
from domain.file_utils import send_to_trash
from domain.scanner import discover_photos

logger = logging.getLogger(__name__)

# Precomputed 32x32 DCT basis matrix for fallback/deterministic DCT
_N_DCT = 32
_DCT_MATRIX = np.zeros((_N_DCT, _N_DCT), dtype=np.float32)
for _i in range(_N_DCT):
    for _j in range(_N_DCT):
        if _i == 0:
            _DCT_MATRIX[_i, _j] = 1.0 / np.sqrt(_N_DCT)
        else:
            _DCT_MATRIX[_i, _j] = np.sqrt(2.0 / _N_DCT) * np.cos(np.pi * (2 * _j + 1) * _i / (2.0 * _N_DCT))

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    _CV2_AVAILABLE = False

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

    @staticmethod
    def compute_perceptual_hash(file_path: Path) -> tuple[int | None, float, np.ndarray | None]:
        """
        Computes a 128-bit perceptual hash (64-bit DCT pHash + 64-bit dHash),
        image aspect ratio, and an 8x8 RGB color thumbnail.
        Returns (hash_128, aspect_ratio, color_thumb).
        If loading fails or file is not an image, returns (None, 0.0, None).
        """
        try:
            with Image.open(file_path) as img:
                img = ImageOps.exif_transpose(img)
                w, h = img.size
                if w <= 0 or h <= 0:
                    return None, 0.0, None
                ar = float(w) / float(h)

                # 8x8 RGB color thumbnail for color validation
                color_thumb = np.asarray(
                    img.convert("RGB").resize((8, 8), Image.Resampling.BILINEAR),
                    dtype=np.uint8,
                )

                # 1. 64-bit DCT pHash
                p_img = img.convert("L").resize((32, 32), Image.Resampling.BILINEAR)
                arr = np.float32(p_img)
                if _CV2_AVAILABLE and cv2 is not None:
                    try:
                        dct = cv2.dct(arr)
                    except Exception:
                        dct = _DCT_MATRIX @ arr @ _DCT_MATRIX.T
                else:
                    dct = _DCT_MATRIX @ arr @ _DCT_MATRIX.T

                dct_low = dct[:8, :8]
                med = np.median(dct_low[1:, 1:])
                phash_bits = (dct_low > med).flatten()
                phash_int = int.from_bytes(np.packbits(phash_bits).tobytes(), "big")

                # 2. 64-bit difference hash (dHash)
                d_img = img.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
                d_arr = np.asarray(d_img)
                dhash_bits = (d_arr[:, 1:] > d_arr[:, :-1]).flatten()
                dhash_int = int.from_bytes(np.packbits(dhash_bits).tobytes(), "big")

                combined = (phash_int << 64) | dhash_int
                return combined, ar, color_thumb
        except Exception:
            return None, 0.0, None

    def scan_directories_for_duplicates(
        self,
        sources: list[str | Path],
        recursive: bool = True,
        method: str = "visual",
        max_distance: int = 8,
    ) -> list[dict[str, Any]]:
        """
        Scans directories for duplicate images.

        Modes:
        - 'visual': Computes perceptual hash (pHash/dHash) and color signature in addition
          to fast SHA-256 pre-clustering. Catches exact duplicates as well as mobile copies
          (e.g. 'photo (1).jpg' with modified EXIF timestamps or slight recompression).
        - 'exact': Strict byte-for-byte SHA-256 matching.
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

        if method == "exact":
            return self._scan_exact_duplicates(valid_paths)
        else:
            return self._scan_visual_duplicates(valid_paths, max_distance=max_distance)

    def _scan_exact_duplicates(self, valid_paths: list[Path]) -> list[dict[str, Any]]:
        """Scans directories for exact byte-for-byte duplicate images using SHA-256."""
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
                file_items = self._build_file_items(files)
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

    def _scan_visual_duplicates(
        self, valid_paths: list[Path], max_distance: int = 8
    ) -> list[dict[str, Any]]:
        """
        Scans directories for duplicate images using perceptual hashing (pHash + dHash)
        combined with exact SHA-256 matching.
        Catches exact clones, mobile duplicates with modified EXIF, and recompressed copies.
        """
        n = len(valid_paths)
        parent = list(range(n))
        members = {i: [i] for i in range(n)}

        def find(i: int) -> int:
            path = []
            while parent[i] != i:
                path.append(i)
                i = parent[i]
            for node in path:
                parent[node] = i
            return i

        def union(i: int, j: int):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j
                members[root_j].extend(members.pop(root_i))

        # Pass 1: Quick SHA-256 matching for exact identical byte files
        size_groups: dict[int, list[int]] = {}
        for idx, p in enumerate(valid_paths):
            try:
                st = p.stat()
                if st.st_size > 0:
                    size_groups.setdefault(st.st_size, []).append(idx)
            except Exception:
                pass

        sha_map: dict[str, int] = {}
        exact_hashes: dict[int, str] = {}
        for size, indices in size_groups.items():
            if len(indices) >= 2:
                for idx in indices:
                    try:
                        f_hash = self.compute_file_hash(valid_paths[idx])
                        exact_hashes[idx] = f_hash
                        if f_hash in sha_map:
                            union(idx, sha_map[f_hash])
                        else:
                            sha_map[f_hash] = idx
                    except Exception:
                        pass

        # Pass 2: Concurrent perceptual hash extraction
        workers = min(8, os.cpu_count() or 4)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            phashes = list(executor.map(self.compute_perceptual_hash, valid_paths))

        def compatible(i: int, j: int) -> bool:
            if i in exact_hashes and exact_hashes.get(i) == exact_hashes.get(j):
                return True
            h_i, ar_i, c_i = phashes[i]
            h_j, ar_j, c_j = phashes[j]
            if h_i is None or c_i is None or h_j is None or c_j is None:
                return False
            if abs(ar_i - ar_j) / max(ar_i, ar_j) > 0.08:
                return False
            if (h_i ^ h_j).bit_count() > max_distance:
                return False
            # Flat images share perceptual hashes even when their actual colors differ.
            if (np.std(c_i) < 5 or np.std(c_j) < 5) and not np.array_equal(c_i, c_j):
                return False
            return float(np.mean(np.abs(c_i.astype(float) - c_j.astype(float)))) <= 12.0

        # Pass 3: A group is safe only when every member matches every other member.
        for i in range(n):
            for j in range(i + 1, n):
                root_i, root_j = find(i), find(j)
                if root_i != root_j and all(
                    compatible(a, b) for a in members[root_i] for b in members[root_j]
                ):
                    union(i, j)

        # Pass 4: Build duplicate sets from clusters
        clusters: dict[int, list[Path]] = {}
        for idx, p in enumerate(valid_paths):
            clusters.setdefault(find(idx), []).append(p)

        duplicate_sets: list[dict[str, Any]] = []
        set_idx = 1

        for root_idx, files in clusters.items():
            if len(files) >= 2:
                file_items = self._build_file_items(files)
                if len(file_items) >= 2:
                    sample_name = file_items[0]["filename"]
                    single_size = max(f["size"] for f in file_items)
                    total_size = sum(f["size"] for f in file_items)
                    potential_savings = total_size - file_items[0]["size"]

                    # Representative hash
                    try:
                        rep_hash = self.compute_file_hash(files[0])
                    except Exception:
                        rep_hash = f"group_{set_idx}"

                    duplicate_sets.append({
                        "set_id": f"set_{set_idx}",
                        "hash": rep_hash,
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

    @staticmethod
    def _build_file_items(files: list[Path]) -> list[dict[str, Any]]:
        """Build structured metadata dictionaries for a list of file paths."""
        file_items = []
        for p in files:
            try:
                scan_hash = DuplicateService.compute_file_hash(p)
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
                    "scan_hash": scan_hash,
                    "is_recommended_keep": False,
                    "is_selected_for_removal": False,
                })
            except Exception:
                pass
        return file_items

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
                    # Priority: Original clean name first -> Earliest mtime -> Earliest ctime -> Shorter filename -> Shorter path
                    return (is_copy, mtime, ctime, len(filename), len(path), path)

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

            # Recalculate potential savings accurately based on files marked for removal
            potential_savings = sum(f.get("size", 0) for f in files if f.get("is_selected_for_removal", False))
            dset["potential_savings"] = potential_savings
            dset["formatted_savings"] = format_bytes(potential_savings)

    def remove_duplicates(
        self,
        file_paths_to_remove: list[str],
        mode: str = "trash",
        progress_cb: Any = None,
        cancel_check: Any = None,
        expected_hashes: dict[str, str] | None = None,
        keepers_by_path: dict[str, str] | None = None,
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
                if expected_hashes is not None:
                    error_count += 1
                continue

            try:
                if expected_hashes is not None:
                    keeper_path = (keepers_by_path or {}).get(p_str)
                    if (not keeper_path or keeper_path == p_str
                            or p_str not in expected_hashes or keeper_path not in expected_hashes
                            or self.compute_file_hash(p) != expected_hashes[p_str]
                            or self.compute_file_hash(Path(keeper_path)) != expected_hashes[keeper_path]):
                        logger.warning("Skipping changed duplicate or keeper: %s", p_str)
                        error_count += 1
                        continue
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
