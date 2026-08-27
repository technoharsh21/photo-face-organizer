"""
Scan Service Module.

Coordinates scan configurations, background scan worker initialization,
pause/resume/cancel state management, crash recovery detection, and history recording.
"""

import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from config import Config
from domain.face_engine import FaceEngine
from domain.scanner import discover_photos
from domain.worker import ScanWorker
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.unknown_face_service import UnknownFaceService

logger = logging.getLogger(__name__)


class ScanService:
    """Manages high-level scan operations, lifecycle, workers, and checkpoint recovery."""

    def __init__(
        self,
        config: Config,
        face_engine: FaceEngine,
        output_service: OutputService,
        unknown_face_service: UnknownFaceService,
        history_service: HistoryService,
        profile_service: ProfileService,
    ):
        self.config = config
        self.face_engine = face_engine
        self.output_service = output_service
        self.unknown_face_service = unknown_face_service
        self.history_service = history_service
        self.profile_service = profile_service

        self.current_worker: ScanWorker | None = None
        self.active_scan_data: dict[str, Any] | None = None

    def check_interrupted_scans(self) -> list[dict[str, Any]]:
        """
        Scans self.config.scans_dir for any scans with status 'Running' or 'Paused' in checkpoint.
        Used for startup crash recovery dialog.
        """
        interrupted = []
        for s_dir in self.config.scans_dir.iterdir():
            if s_dir.is_dir():
                cp_file = s_dir / "checkpoint.json"
                scan_file = s_dir / "scan.json"
                if cp_file.exists() and scan_file.exists():
                    try:
                        with open(cp_file, "r", encoding="utf-8") as f:
                            cp_data = json.load(f)
                        with open(scan_file, "r", encoding="utf-8") as f:
                            scan_data = json.load(f)

                        status = cp_data.get("status")
                        if status in {"Running", "Paused", "Interrupted"}:
                            scan_data["checkpoint"] = cp_data
                            interrupted.append(scan_data)
                    except Exception:
                        pass
        return interrupted

    def discard_recovery(self, scan_id: str):
        """
        Removes recovery checkpoint information for scan_id without touching photos.
        """
        s_dir = self.config.scans_dir / scan_id
        if s_dir.exists():
            cp_file = s_dir / "checkpoint.json"
            if cp_file.exists():
                cp_file.unlink()

            # Record scan as Interrupted in history
            scan_file = s_dir / "scan.json"
            if scan_file.exists():
                try:
                    with open(scan_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["status"] = "Interrupted"
                    self.history_service.record_scan(data)
                except Exception:
                    pass

    def start_new_scan(
        self,
        sources: list[str],
        profile_ids: list[str],
        output_dir: str,
        recursive: bool = True,
        device_preference: str = "Auto",
        performance_mode: str = "Balanced",
        threshold: float = 50.0,
    ) -> tuple[ScanWorker, dict[str, Any]]:
        """
        Initializes and returns a ScanWorker thread ready to start scanning.
        """
        scan_id = str(uuid.uuid4())
        scan_dir = self.config.scans_dir / scan_id
        scan_dir.mkdir(parents=True, exist_ok=True)

        # 1. Discover photo files
        discovered_paths = discover_photos(sources, recursive=recursive)

        # 2. Fetch full profiles with encodings
        selected_profiles = []
        for p_id in profile_ids:
            p_data = self.profile_service.get_profile(p_id)
            if p_data:
                selected_profiles.append(p_data)

        # 3. Configure face engine device
        active_device = self.face_engine.set_device_preference(device_preference)

        start_iso = datetime.datetime.now().isoformat()
        scan_meta = {
            "scan_id": scan_id,
            "status": "Running",
            "start_time": start_iso,
            "sources": sources,
            "profile_ids": profile_ids,
            "profile_names": [p["name"] for p in selected_profiles],
            "output_dir": output_dir,
            "recursive": recursive,
            "device_preference": device_preference,
            "active_device": active_device,
            "performance_mode": performance_mode,
            "threshold": threshold,
            "total_files": len(discovered_paths),
        }

        # Save scan.json
        with open(scan_dir / "scan.json", "w", encoding="utf-8") as f:
            json.dump(scan_meta, f, indent=2)

        checkpoint_file = scan_dir / "checkpoint.json"

        # Create Worker Thread
        worker = ScanWorker(
            scan_id=scan_id,
            files=discovered_paths,
            profiles=selected_profiles,
            output_dir=Path(output_dir),
            checkpoint_file=checkpoint_file,
            face_engine=self.face_engine,
            output_service=self.output_service,
            unknown_face_service=self.unknown_face_service,
            threshold=threshold,
            performance_mode=performance_mode,
            start_index=0,
        )

        self.current_worker = worker
        self.active_scan_data = scan_meta

        # Connect worker completion to update scan metadata and history
        worker.finished_signal.connect(self._on_worker_finished)

        return worker, scan_meta

    def resume_scan(self, scan_id: str) -> tuple[ScanWorker, dict[str, Any]] | None:
        """
        Resumes a paused or interrupted scan using its checkpoint file.
        """
        scan_dir = self.config.scans_dir / scan_id
        checkpoint_file = scan_dir / "checkpoint.json"
        scan_file = scan_dir / "scan.json"

        if not (checkpoint_file.exists() and scan_file.exists()):
            return None

        with open(scan_file, "r", encoding="utf-8") as f:
            scan_meta = json.load(f)
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            cp_data = json.load(f)

        sources = scan_meta.get("sources", [])
        recursive = scan_meta.get("recursive", True)
        discovered_paths = discover_photos(sources, recursive=recursive)

        profile_ids = scan_meta.get("profile_ids", [])
        selected_profiles = [
            p for p in [self.profile_service.get_profile(p_id) for p_id in profile_ids] if p is not None
        ]

        start_index = cp_data.get("current_index", 0)

        worker = ScanWorker(
            scan_id=scan_id,
            files=discovered_paths,
            profiles=selected_profiles,
            output_dir=Path(scan_meta["output_dir"]),
            checkpoint_file=checkpoint_file,
            face_engine=self.face_engine,
            output_service=self.output_service,
            unknown_face_service=self.unknown_face_service,
            threshold=scan_meta.get("threshold", 50.0),
            performance_mode=scan_meta.get("performance_mode", "Balanced"),
            start_index=start_index,
            initial_stats=cp_data,
        )

        self.current_worker = worker
        self.active_scan_data = scan_meta

        worker.finished_signal.connect(self._on_worker_finished)
        return worker, scan_meta

    def pause_active_scan(self):
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.pause()

    def resume_active_scan(self):
        if self.current_worker:
            self.current_worker.resume()

    def cancel_active_scan(self):
        if self.current_worker:
            self.current_worker.cancel()

    def _on_worker_finished(self, summary: dict[str, Any]):
        """Handler called when ScanWorker finishes."""
        scan_id = summary.get("scan_id")
        if self.active_scan_data and self.active_scan_data.get("scan_id") == scan_id:
            record = self.active_scan_data.copy()
            record.update(summary)
            record["end_time"] = datetime.datetime.now().isoformat()
            # Save results.json
            s_dir = self.config.scans_dir / scan_id
            if s_dir.exists():
                with open(s_dir / "results.json", "w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2)

            # Record in history service
            self.history_service.record_scan(record)
