"""
Solo Scan Worker Pipeline.

Executes dedicated deep multi-scale solo face detection (2x upsampling), single-person encoding,
solo profile matching, and target person photo copying in a background QThread.

RULES:
- ONLY copies matched solo photos to person folders.
- NEVER creates a 'No Match' folder (unmatched & group photos are not copied).
- Collects copied file pairs for optional post-scan 100% verification and safe source cleanup.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from domain.face_engine import FaceEngine
from domain.image_loader import load_image
from domain.solo_matcher import SoloFaceMatcher
from services.face_cache_service import FaceCacheService
from services.output_service import OutputService
from services.unknown_face_service import UnknownFaceService

logger = logging.getLogger(__name__)


class SoloScanWorker(QThread):
    """
    Background worker thread executing the solo photo scanner pipeline.
    Emits progress, status changes, and completion signals.
    """

    progress_signal = Signal(dict)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(
        self,
        scan_id: str,
        files: list[Path],
        profiles: list[dict[str, Any]],
        output_dir: Path,
        checkpoint_file: Path,
        face_engine: FaceEngine,
        output_service: OutputService,
        unknown_face_service: UnknownFaceService,
        face_cache_service: FaceCacheService | None = None,
        threshold: float = 70.0,
        performance_mode: str = "Maximum Performance",
        operation_mode: str = "copy",
        start_index: int = 0,
        initial_stats: dict[str, Any] | None = None,
        all_system_profiles: list[dict[str, Any]] | None = None,
    ):
        super().__init__()
        self.scan_id = scan_id
        self.files = files
        self.profiles = profiles
        self.all_system_profiles = all_system_profiles or profiles
        self.output_dir = Path(output_dir)
        self.checkpoint_file = Path(checkpoint_file)
        self.face_engine = face_engine
        self.output_service = output_service
        self.unknown_face_service = unknown_face_service
        self.face_cache_service = face_cache_service
        self.threshold = threshold
        self.performance_mode = performance_mode
        self.operation_mode = operation_mode  # "copy" or "move"
        self.start_index = start_index

        self._is_paused = False
        self._is_cancelled = False

        # Statistics & Audit Tracking
        init = initial_stats or {}
        self.total_files = len(files)
        self.processed_count = init.get("processed_count", 0)
        self.matched_count = init.get("matched_count", 0)
        self.no_match_count = init.get("no_match_count", 0)
        self.unknown_faces_count = init.get("unknown_faces_count", 0)
        self.skipped_count = init.get("skipped_count", 0)
        self.error_count = init.get("error_count", 0)
        self.results_by_person: dict[str, int] = init.get("results_by_person", {})
        self.processed_files: set[str] = set(init.get("processed_files", []))
        self.errors_log: list[dict[str, str]] = init.get("errors_log", [])
        self.source_to_output_map: dict[str, list[str]] = init.get("source_to_output_map", {})
        self.copied_file_pairs: list[tuple[str, str]] = init.get("copied_file_pairs", [])

        self.matcher = SoloFaceMatcher(face_engine=face_engine, threshold=threshold)

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def run(self):
        import os  # Explicit local import: safety guard for PyInstaller --windowed bundled exe
        start_time = time.time()
        logger.info(f"Starting deep solo scan worker {self.scan_id} on {self.total_files} files (mode={self.operation_mode}).")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        cpu_count = os.cpu_count() or 4
        if self.performance_mode == "Maximum Performance":
            max_workers = max(4, cpu_count * 2)
        elif self.performance_mode == "Balanced":
            max_workers = max(2, cpu_count // 2)
        else:
            max_workers = max(1, cpu_count // 4)

        # Cap GPU workers to avoid VRAM saturation on consumer GPUs (e.g. GTX 1650 = 4GB VRAM).
        if getattr(self.face_engine, "gpu_available", False):
            max_workers = min(max_workers, 4)

        batch_size = max(4, max_workers * 2)
        remaining_files = [f for f in self.files[self.start_index:] if str(f) not in self.processed_files]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for b_idx in range(0, len(remaining_files), batch_size):
                if self._is_cancelled:
                    logger.info("Solo scan worker cancelled by user.")
                    self._save_checkpoint("Cancelled", self.processed_count)
                    self.finished_signal.emit(self._build_summary("Cancelled", time.time() - start_time))
                    return

                while self._is_paused and not self._is_cancelled:
                    time.sleep(0.2)
                    self._save_checkpoint("Paused", self.processed_count)

                batch = remaining_files[b_idx : b_idx + batch_size]
                future_to_file = {executor.submit(self._process_file, f, 0): f for f in batch}

                for future in as_completed(future_to_file):
                    f_path = future_to_file[future]
                    str_path = str(f_path)
                    try:
                        future.result()
                    except Exception as exc:
                        self.skipped_count += 1
                        self.error_count += 1
                        self.errors_log.append({"file": str_path, "error": str(exc)})

                    self.processed_count += 1
                    self.processed_files.add(str_path)

                    if self.processed_count % 5 == 0 or self.processed_count == self.total_files:
                        self._save_checkpoint("Running", self.processed_count)

                    elapsed = time.time() - start_time
                    files_per_sec = self.processed_count / elapsed if elapsed > 0 else 0
                    rem_count = self.total_files - self.processed_count
                    eta_seconds = rem_count / files_per_sec if files_per_sec > 0 else 0

                    self.progress_signal.emit({
                        "scan_id": self.scan_id,
                        "current_file": f_path.name,
                        "current_index": self.processed_count,
                        "total_files": self.total_files,
                        "progress_percent": round((self.processed_count / self.total_files) * 100.0, 1),
                        "processed": self.processed_count,
                        "matched": self.matched_count,
                        "no_match": self.no_match_count,
                        "unknown_faces": self.unknown_faces_count,
                        "skipped": self.skipped_count,
                        "errors": self.error_count,
                        "speed_fps": round(files_per_sec, 2),
                        "eta_seconds": round(eta_seconds, 1),
                    })

        # Solo scan completed
        elapsed_total = time.time() - start_time
        self._save_checkpoint("Completed", self.total_files)
        summary = self._build_summary("Completed", elapsed_total)
        self.finished_signal.emit(summary)

    def _process_file(self, file_path: Path, index: int):
        pil_img, err = load_image(file_path)
        if pil_img is None:
            self.skipped_count += 1
            self.error_count += 1
            self.errors_log.append({"file": str(file_path), "error": err or "Unreadable image"})
            self.source_to_output_map[str(file_path)] = ["Skipped/Unreadable"]
            return

        try:
            # Check Disk Cache
            cached = self.face_cache_service.get_cached_faces(file_path) if self.face_cache_service else None
            if cached is not None:
                face_locations, face_encodings = cached
                face_crops = self.face_engine.extract_faces(pil_img, face_locations)
            else:
                # 1. Single-pass detection and embedding extraction
                if hasattr(self.face_engine, "detect_and_embed_faces"):
                    face_locations, face_encodings, face_crops = self.face_engine.detect_and_embed_faces(pil_img)
                else:
                    face_locations = self.face_engine.detect_faces(pil_img)
                    face_encodings = self.face_engine.create_embeddings(pil_img, face_locations)
                    face_crops = self.face_engine.extract_faces(pil_img, face_locations)

                # Retry with upsample=2 if 0 faces found
                if not face_locations:
                    face_locations = self.face_engine.detect_faces(pil_img, upsample_num_times=2)
                    if face_locations:
                        face_encodings = self.face_engine.create_embeddings(pil_img, face_locations)
                        face_crops = self.face_engine.extract_faces(pil_img, face_locations)

                if self.face_cache_service:
                    self.face_cache_service.save_cached_faces(file_path, face_locations, face_encodings)

            if not face_locations:
                self.no_match_count += 1
                self.source_to_output_map[str(file_path)] = ["No faces detected"]
                return

            # 2. Evaluate solo and exclusive group solo matches
            matched_person_names, face_results = self.matcher.evaluate_solo_photo_matches(
                face_encodings=face_encodings,

                face_locations=face_locations,
                profiles=self.profiles,
                all_system_profiles=self.all_system_profiles,
            )

            # 4. Route copies ONLY IF matched to a person profile
            if matched_person_names:
                self.matched_count += 1
                output_targets = []
                for p_name in sorted(matched_person_names):
                    self.results_by_person[p_name] = self.results_by_person.get(p_name, 0) + 1
                    clean_name = self.output_service.sanitize_folder_name(p_name)
                    person_folder = self.output_dir / clean_name
                    success, target_path, status = self.output_service.copy_photo_to_destination(
                        file_path, person_folder, folder_key=clean_name
                    )
                    if target_path is not None:
                        output_targets.append(str(target_path))
                        self.copied_file_pairs.append((str(file_path), str(target_path)))
                    else:
                        output_targets.append(f"Copy Status: {status}")

                self.source_to_output_map[str(file_path)] = output_targets
            else:
                # Unmatched photo -> Increment no_match counter, DO NOT create 'No Match' folder
                self.no_match_count += 1
                if len(face_locations) == 1 and face_results and face_crops:
                    res = face_results[0]
                    stored = self.unknown_face_service.store_unknown_face(
                        face_crop=face_crops[0],
                        face_encoding=res.face_encoding,
                        source_photo_path=str(file_path),
                        bounding_box=list(res.bounding_box),
                        scan_id=self.scan_id,
                    )
                    if stored is not None:
                        self.unknown_faces_count += 1
                    self.source_to_output_map[str(file_path)] = ["Unmatched Single Face (No Output Copy)"]
                else:
                    self.source_to_output_map[str(file_path)] = [f"Filtered Out Group Photo ({len(face_locations)} faces)"]


        except Exception as e:
            logger.error(f"Error processing solo photo {file_path}: {e}")
            self.error_count += 1
            self.errors_log.append({"file": str(file_path), "error": str(e)})
            self.source_to_output_map[str(file_path)] = [f"Error: {e!s}"]

    def _save_checkpoint(self, status: str, current_index: int):
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_data = {
            "scan_id": self.scan_id,
            "status": status,
            "current_index": current_index,
            "total_files": self.total_files,
            "processed_count": self.processed_count,
            "matched_count": self.matched_count,
            "no_match_count": self.no_match_count,
            "unknown_faces_count": self.unknown_faces_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "results_by_person": self.results_by_person,
            "processed_files": list(self.processed_files),
            "errors_log": self.errors_log,
            "source_to_output_map": self.source_to_output_map,
            "copied_file_pairs": self.copied_file_pairs,
            "operation_mode": self.operation_mode,
        }
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write solo checkpoint: {e}")

    def _build_summary(self, final_status: str, duration_seconds: float) -> dict[str, Any]:
        total_accounted = self.matched_count + self.no_match_count + self.skipped_count
        missed_files = max(0, self.total_files - total_accounted)

        return {
            "scan_id": self.scan_id,
            "scan_type": "Solo Scan",
            "status": final_status,
            "total_files": self.total_files,
            "processed": self.processed_count,
            "matched": self.matched_count,
            "no_match": self.no_match_count,
            "unknown_faces": self.unknown_faces_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
            "total_accounted": total_accounted,
            "missed_files": missed_files,
            "reconciliation_percent": round((total_accounted / self.total_files) * 100.0, 1) if self.total_files > 0 else 100.0,
            "results_by_person": self.results_by_person,
            "duration_seconds": round(duration_seconds, 2),
            "output_dir": str(self.output_dir),
            "errors_log": self.errors_log,
            "source_to_output_map": self.source_to_output_map,
            "copied_file_pairs": self.copied_file_pairs,
            "operation_mode": self.operation_mode,
        }
