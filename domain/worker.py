"""
Processing Worker Pipeline.

Executes face detection, encoding, profile matching, output copying, and unknown face registration
safely in a background thread while updating Qt UI signals.
Supports Pause, Resume, Cancel, State Checkpointing, and Source File Audit Reconciliation.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from domain.face_engine import FaceEngine
from domain.image_loader import load_image
from domain.matcher import FaceMatcher
from services.output_service import OutputService
from services.unknown_face_service import UnknownFaceService

logger = logging.getLogger(__name__)


class ScanWorkerSignals:
    """Convenience data passed through Qt signals."""
    def __init__(self, current_file: str, progress_percent: float, stats: dict[str, Any]):
        self.current_file = current_file
        self.progress_percent = progress_percent
        self.stats = stats


class ScanWorker(QThread):
    """
    Background worker thread executing the photo scanner pipeline safely and sequentially.
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
        threshold: float = 50.0,
        performance_mode: str = "Balanced",
        start_index: int = 0,
        initial_stats: dict[str, Any] | None = None,
    ):
        super().__init__()
        self.scan_id = scan_id
        self.files = files
        self.profiles = profiles
        self.output_dir = Path(output_dir)
        self.checkpoint_file = Path(checkpoint_file)
        self.face_engine = face_engine
        self.output_service = output_service
        self.unknown_face_service = unknown_face_service
        self.threshold = threshold
        self.performance_mode = performance_mode
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

        self.matcher = FaceMatcher(face_engine=face_engine, threshold=threshold)

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
        start_time = time.time()
        logger.info(f"Starting scan worker {self.scan_id} on {self.total_files} files.")

        for i in range(self.start_index, self.total_files):
            # Check pause loop
            while self._is_paused and not self._is_cancelled:
                time.sleep(0.2)
                self._save_checkpoint("Paused", i)

            # Check cancel signal
            if self._is_cancelled:
                logger.info("Scan worker cancelled by user.")
                self._save_checkpoint("Cancelled", i)
                self.finished_signal.emit(self._build_summary("Cancelled", time.time() - start_time))
                return

            file_path = self.files[i]
            str_path = str(file_path)

            if str_path in self.processed_files:
                continue

            # Throttle if Eco mode
            if self.performance_mode == "Eco":
                time.sleep(0.05)

            # Process single file sequentially (thread-safe for dlib / C++ bindings)
            self._process_file(file_path, i)

            self.processed_count = i + 1
            self.processed_files.add(str_path)

            # Save checkpoint periodically
            if (i + 1) % 5 == 0 or i == self.total_files - 1:
                self._save_checkpoint("Running", i + 1)

            # Emit progress update
            elapsed = time.time() - start_time
            files_per_sec = self.processed_count / elapsed if elapsed > 0 else 0
            remaining_files = self.total_files - self.processed_count
            eta_seconds = remaining_files / files_per_sec if files_per_sec > 0 else 0

            self.progress_signal.emit({
                "scan_id": self.scan_id,
                "current_file": file_path.name,
                "current_index": i + 1,
                "total_files": self.total_files,
                "progress_percent": round(((i + 1) / self.total_files) * 100.0, 1),
                "processed": self.processed_count,
                "matched": self.matched_count,
                "no_match": self.no_match_count,
                "unknown_faces": self.unknown_faces_count,
                "skipped": self.skipped_count,
                "errors": self.error_count,
                "speed_fps": round(files_per_sec, 2),
                "eta_seconds": round(eta_seconds, 1),
            })

        # Scan completed successfully
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
            # 1. Detect faces
            face_locations = self.face_engine.detect_faces(pil_img)

            if not face_locations:
                self.no_match_count += 1
                copies = self.output_service.process_photo_output(
                    source_path=file_path,
                    output_base_dir=self.output_dir,
                    matched_profile_names=set(),
                )
                self.source_to_output_map[str(file_path)] = [
                    str(target) for (_, target, _) in copies if target is not None
                ]
                return

            # 2. Extract face crops and generate encodings
            face_encodings = self.face_engine.create_embeddings(pil_img, face_locations)
            face_crops = self.face_engine.extract_faces(pil_img, face_locations)

            # 3. Evaluate photo matches
            matched_person_names, face_results = self.matcher.evaluate_photo_matches(
                face_encodings=face_encodings,
                face_locations=face_locations,
                profiles=self.profiles,
            )

            # Update unknown faces
            for res, crop in zip(face_results, face_crops):
                if not res.is_match or not res.matched_profile_name:
                    self.unknown_faces_count += 1
                    self.unknown_face_service.store_unknown_face(
                        face_crop=crop,
                        face_encoding=res.face_encoding,
                        source_photo_path=str(file_path),
                        bounding_box=list(res.bounding_box),
                        scan_id=self.scan_id,
                    )

            # 4. Route photo output copies
            if matched_person_names:
                self.matched_count += 1
                for p_name in matched_person_names:
                    self.results_by_person[p_name] = self.results_by_person.get(p_name, 0) + 1
            else:
                self.no_match_count += 1

            copies = self.output_service.process_photo_output(
                source_path=file_path,
                output_base_dir=self.output_dir,
                matched_profile_names=matched_person_names,
            )

            output_targets = []
            for _, target, status in copies:
                if target is not None:
                    output_targets.append(str(target))
                else:
                    output_targets.append(f"Output Status: {status}")
                    if "error" in status.lower():
                        self.error_count += 1
                        self.errors_log.append({"file": str(file_path), "error": status})

            self.source_to_output_map[str(file_path)] = output_targets

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.error_count += 1
            self.errors_log.append({"file": str(file_path), "error": str(e)})
            self.source_to_output_map[str(file_path)] = [f"Error: {e!s}"]

    def _save_checkpoint(self, status: str, current_index: int):
        """Write current scan progress to local checkpoint JSON file."""
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
        }
        try:
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write checkpoint: {e}")

    def _build_summary(self, final_status: str, duration_seconds: float) -> dict[str, Any]:
        total_accounted = self.matched_count + self.no_match_count + self.skipped_count
        missed_files = max(0, self.total_files - total_accounted)

        return {
            "scan_id": self.scan_id,
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
        }
