"""
Find Photos Service & Background Scanning Engine.

Discovers and filters photos of a specific person across multiple directories in real-time.
Supports 'Solo Photos' (only photos where the person is alone) and 'All Photos' (solo + group photos).
Emits matching photos progressively in real-time without blocking the UI.
Original source files are never moved, modified, or permanently duplicated during scanning.
"""

import datetime
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from PySide6.QtCore import QThread, Signal

from domain.face_engine import FaceEngine
from domain.image_loader import is_supported_image, load_image
from domain.scanner import discover_photos
from services.face_cache_service import FaceCacheService

logger = logging.getLogger(__name__)


class FindPhotosWorker(QThread):
    """
    Background worker thread for searching photos of a specific person in real-time.
    Emits matches progressively as soon as they are detected.
    """

    match_found_signal = Signal(dict)
    progress_signal = Signal(int, int, str)
    status_signal = Signal(str)
    finished_signal = Signal(int, int, float, list)

    def __init__(
        self,
        target_profile: dict[str, Any],
        folders: list[str | Path],
        match_type: str = "all",  # "solo" or "all"
        recursive: bool = True,
        threshold: float = 55.0,
        face_engine: FaceEngine | None = None,
        face_cache_service: FaceCacheService | None = None,
    ):
        super().__init__()
        self.target_profile = target_profile
        self.folders = [str(Path(f).resolve()) for f in folders if f]
        self.match_type = match_type.lower()
        self.recursive = recursive
        self.threshold = float(threshold)
        self.face_engine = face_engine
        self.face_cache_service = face_cache_service

        self._is_cancelled = False
        self._is_paused = False
        self.matches: list[dict[str, Any]] = []

    def cancel(self):
        """Cancel scanning safely."""
        self._is_cancelled = True

    def pause(self):
        """Pause scanning."""
        self._is_paused = True

    def resume(self):
        """Resume scanning."""
        self._is_paused = False

    def is_paused(self) -> bool:
        return self._is_paused

    def _prepare_target_embeddings(self) -> list[np.ndarray]:
        """Extract and normalize target profile embeddings."""
        embs = self.target_profile.get("embeddings", [])
        valid_embs = []
        for e in embs:
            arr = np.asarray(e, dtype=np.float64)
            if arr.size > 0:
                valid_embs.append(arr)
        return valid_embs

    def _evaluate_face_match(
        self, face_encoding: np.ndarray, target_embeddings: list[np.ndarray], centroid_arr: np.ndarray | None
    ) -> float:
        """Calculate best match score against target profile embeddings."""
        if not target_embeddings or self.face_engine is None:
            return 0.0

        scores = []
        for ref_emb in target_embeddings:
            score = self.face_engine.calculate_match_score(face_encoding, ref_emb)
            scores.append(score)

        if not scores:
            return 0.0

        sorted_scores = sorted(scores, reverse=True)
        best_score = sorted_scores[0]

        # Consensus boost: if 2+ reference photos agree >= 45%, apply small boost
        if len(sorted_scores) >= 2 and sorted_scores[1] >= 45.0:
            consensus_boost = min(5.0, (sorted_scores[1] / 100.0) * 8.0)
            best_score = min(100.0, best_score + consensus_boost)

        # Centroid comparison
        if centroid_arr is not None and centroid_arr.size > 0:
            centroid_score = self.face_engine.calculate_match_score(face_encoding, centroid_arr)
            if centroid_score > best_score:
                best_score = centroid_score

        return best_score

    def run(self):
        start_time = time.time()
        self.matches.clear()

        if not self.folders or not self.target_profile or self.face_engine is None:
            self.status_signal.emit("Invalid search configuration.")
            self.finished_signal.emit(0, 0, 0.0, [])
            return

        target_name = self.target_profile.get("name", "Person")
        self.status_signal.emit(f"Discovering photos across {len(self.folders)} folder(s)...")

        # Step 1: Discover all photos
        photo_paths = discover_photos(self.folders, recursive=self.recursive)
        total_photos = len(photo_paths)

        if total_photos == 0:
            self.status_signal.emit("No supported photo files found in selected folders.")
            self.finished_signal.emit(0, 0, time.time() - start_time, [])
            return

        target_embeddings = self._prepare_target_embeddings()
        centroid_embedding = self.target_profile.get("centroid_embedding")
        centroid_arr = np.asarray(centroid_embedding, dtype=np.float64) if centroid_embedding else None

        if not target_embeddings and centroid_arr is None:
            self.status_signal.emit(f"Profile '{target_name}' has no reference face photos.")
            self.finished_signal.emit(total_photos, 0, time.time() - start_time, [])
            return

        self.status_signal.emit(f"Searching {total_photos} photos for {target_name} ({self.match_type.title()} Mode)...")

        scanned_count = 0
        matches_found = 0

        for photo_path in photo_paths:
            if self._is_cancelled:
                break

            while self._is_paused and not self._is_cancelled:
                time.sleep(0.1)

            scanned_count += 1
            self.progress_signal.emit(scanned_count, total_photos, photo_path.name)

            # Step 2: Retrieve or compute face encodings & locations
            face_locations: list[tuple[int, int, int, int]] = []
            face_encodings: list[np.ndarray] = []

            # Check cache first
            if self.face_cache_service is not None:
                cached = self.face_cache_service.get_cached_faces(photo_path)
                if cached is not None:
                    face_locations, face_encodings = cached

            # Compute if not in cache
            if not face_locations and not face_encodings:
                try:
                    pil_img, err = load_image(photo_path)
                    if pil_img is None:
                        continue

                    locs, encs, _ = self.face_engine.detect_and_embed_faces(pil_img)
                    face_locations = locs
                    face_encodings = encs

                    # Cache newly computed encodings
                    if self.face_cache_service is not None and encs:
                        try:
                            self.face_cache_service.set_cached_faces(photo_path, locs, encs)
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"Failed to process {photo_path}: {e}")
                    continue

            # If no faces detected, skip
            if not face_encodings:
                continue

            # Step 3: Evaluate Match Criteria
            is_match = False
            best_match_score = 0.0
            best_bbox = (0, 0, 0, 0)

            if self.match_type == "solo":
                # Solo Photos Mode: exactly 1 face must be detected in the entire photo
                if len(face_encodings) == 1:
                    score = self._evaluate_face_match(face_encodings[0], target_embeddings, centroid_arr)
                    if score >= self.threshold:
                        is_match = True
                        best_match_score = score
                        if face_locations:
                            best_bbox = face_locations[0]
            else:
                # All Photos Mode: at least one detected face must match the target profile
                for idx, enc in enumerate(face_encodings):
                    score = self._evaluate_face_match(enc, target_embeddings, centroid_arr)
                    if score >= self.threshold and score > best_match_score:
                        is_match = True
                        best_match_score = score
                        if idx < len(face_locations):
                            best_bbox = face_locations[idx]

            # Step 4: Stream Real-Time Match
            if is_match:
                matches_found += 1
                try:
                    st = photo_path.stat()
                    file_size = st.st_size
                    file_mtime = st.st_mtime
                    mtime_str = datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    file_size = 0
                    file_mtime = 0
                    mtime_str = "Unknown"

                match_record = {
                    "id": str(uuid.uuid4()),
                    "path": str(photo_path),
                    "filename": photo_path.name,
                    "folder": str(photo_path.parent),
                    "size": file_size,
                    "mtime": file_mtime,
                    "formatted_mtime": mtime_str,
                    "match_score": round(best_match_score, 1),
                    "face_count": len(face_encodings),
                    "bbox": list(best_bbox),
                    "person_name": target_name,
                    "person_id": self.target_profile.get("id"),
                    "match_type": self.match_type,
                    "is_selected": False,
                }
                self.matches.append(match_record)
                self.match_found_signal.emit(match_record)

        elapsed_time = time.time() - start_time
        status_msg = "Search canceled." if self._is_cancelled else f"Scan complete! Found {matches_found} matching photos in {elapsed_time:.1f}s."
        self.status_signal.emit(status_msg)
        self.finished_signal.emit(scanned_count, matches_found, elapsed_time, self.matches)


class FindPhotosService:
    """Service to handle photo saving, export, and safe file copy operations."""

    @staticmethod
    def get_non_conflicting_path(target_folder: Path, original_filename: str) -> Path:
        """
        Generate a target path in target_folder that does not conflict with existing files.
        Example: photo.jpg -> photo_1.jpg -> photo_2.jpg.
        """
        target_folder.mkdir(parents=True, exist_ok=True)
        dest_path = target_folder / original_filename
        if not dest_path.exists():
            return dest_path

        stem = dest_path.stem
        suffix = dest_path.suffix
        counter = 1
        while True:
            candidate = target_folder / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def save_single_photo(self, source_path_str: str, destination_dir_or_file: str | Path) -> tuple[bool, Path | None, str]:
        """
        Safely copy a single matched photo to a chosen destination directory or file path.
        Preserves original file metadata without modifying original.
        """
        src = Path(source_path_str)
        if not src.exists():
            return False, None, f"Source file does not exist: {src}"

        dest_target = Path(destination_dir_or_file)

        try:
            if dest_target.is_dir() or not dest_target.suffix:
                dest_target.mkdir(parents=True, exist_ok=True)
                final_dest = self.get_non_conflicting_path(dest_target, src.name)
            else:
                dest_target.parent.mkdir(parents=True, exist_ok=True)
                final_dest = dest_target

            shutil.copy2(src, final_dest)
            return True, final_dest, "Saved successfully"
        except Exception as e:
            logger.error(f"Failed to save photo {src} -> {dest_target}: {e}")
            return False, None, str(e)

    def save_multiple_photos(
        self,
        source_paths: list[str],
        destination_folder: str | Path,
        progress_cb: Any = None,
        cancel_check: Any = None,
    ) -> tuple[int, int, list[Path]]:
        """
        Safely copy multiple matched photos into a destination folder with conflict resolution.
        Returns (success_count, error_count, saved_paths).
        """
        dest_dir = Path(destination_folder)
        dest_dir.mkdir(parents=True, exist_ok=True)

        success_count = 0
        error_count = 0
        saved_paths: list[Path] = []
        total = len(source_paths)

        for idx, src_str in enumerate(source_paths):
            if cancel_check and cancel_check():
                break

            src = Path(src_str)
            if progress_cb:
                progress_cb(idx + 1, total, src.name)

            if not src.exists():
                error_count += 1
                continue

            try:
                target_path = self.get_non_conflicting_path(dest_dir, src.name)
                shutil.copy2(src, target_path)
                saved_paths.append(target_path)
                success_count += 1
            except Exception as e:
                logger.error(f"Error copying {src} to {dest_dir}: {e}")
                error_count += 1

        return success_count, error_count, saved_paths
