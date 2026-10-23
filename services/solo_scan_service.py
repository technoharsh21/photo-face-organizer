"""
Solo Scan Service Module.

Coordinates dedicated solo scan worker lifecycle, checkpointing,
and post-scan Copy-then-Verify-then-Confirm Delete ("Move Mode") operations.
"""

import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from config import Config
from domain.face_engine import FaceEngine
from domain.file_utils import trash_verified_sources, verify_copy_pairs
from domain.scanner import discover_photos
from domain.solo_worker import SoloScanWorker
from services.face_cache_service import FaceCacheService
from services.history_service import HistoryService
from services.output_service import OutputService
from services.profile_service import ProfileService
from services.unknown_face_service import UnknownFaceService

logger = logging.getLogger(__name__)


class SoloScanService:
    """Manages dedicated solo scan lifecycle and safe post-scan file verification."""

    def __init__(
        self,
        config: Config,
        face_engine: FaceEngine,
        output_service: OutputService,
        unknown_face_service: UnknownFaceService,
        history_service: HistoryService,
        profile_service: ProfileService,
        face_cache_service: FaceCacheService | None = None,
    ):
        self.config = config
        self.face_engine = face_engine
        self.output_service = output_service
        self.unknown_face_service = unknown_face_service
        self.history_service = history_service
        self.profile_service = profile_service
        self.face_cache_service = face_cache_service

        self.current_worker: SoloScanWorker | None = None
        self.active_scan_data: dict[str, Any] | None = None
        self._verified_copies: dict[str, tuple[str, list[str]]] = {}

    def start_solo_scan(
        self,
        sources: list[str],
        profile_ids: list[str],
        output_dir: str,
        recursive: bool = True,
        performance_mode: str = "Maximum Performance",
        operation_mode: str = "copy",  # "copy" or "move"
        threshold: float = 70.0,
        allow_distant_photobombers: bool = False,
        min_sharpness: float = 0.0,
        folder_organization: str = "flat",
    ) -> tuple[SoloScanWorker, dict[str, Any]]:
        """
        Initializes and returns a SoloScanWorker thread configured for single-person photo matching.
        """
        scan_id = str(uuid.uuid4())
        scan_dir = self.config.scans_dir / scan_id
        scan_dir.mkdir(parents=True, exist_ok=True)

        # Ensure target output directory exists on disk
        out_p = Path(output_dir)
        try:
            out_p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not pre-create solo output dir {output_dir}: {e}")

        # 1. Fetch selected profiles
        selected_profiles = []
        for p_id in profile_ids:
            p_data = self.profile_service.get_profile(p_id)
            if p_data:
                selected_profiles.append(p_data)

        start_iso = datetime.datetime.now().isoformat()
        scan_meta = {
            "scan_id": scan_id,
            "scan_type": "Solo Scan",
            "status": "Running",
            "start_time": start_iso,
            "sources": sources,
            "profile_ids": profile_ids,
            "profile_names": [p["name"] for p in selected_profiles],
            "output_dir": output_dir,
            "recursive": recursive,
            "performance_mode": performance_mode,
            "operation_mode": operation_mode,
            "folder_organization": folder_organization,
            "threshold": threshold,
            "allow_distant_photobombers": allow_distant_photobombers,
            "min_sharpness": min_sharpness,
            "total_files": 0,
        }

        # Save scan.json
        with open(scan_dir / "scan.json", "w", encoding="utf-8") as f:
            json.dump(scan_meta, f, indent=2)

        checkpoint_file = scan_dir / "checkpoint.json"

        all_sys_profiles = self.profile_service.list_profiles()

        # Create Worker Thread with background discovery
        worker = SoloScanWorker(
            scan_id=scan_id,
            files=[],
            sources=sources,
            recursive=recursive,
            profiles=selected_profiles,
            output_dir=Path(output_dir),
            checkpoint_file=checkpoint_file,
            face_engine=self.face_engine,
            output_service=self.output_service,
            unknown_face_service=self.unknown_face_service,
            face_cache_service=self.face_cache_service,
            threshold=threshold,
            performance_mode=performance_mode,
            operation_mode=operation_mode,
            folder_organization=folder_organization,
            start_index=0,
            all_system_profiles=all_sys_profiles,
            allow_distant_photobombers=allow_distant_photobombers,
            min_sharpness=min_sharpness,
        )

        self.current_worker = worker
        self.active_scan_data = scan_meta

        worker.finished_signal.connect(self._on_worker_finished)
        return worker, scan_meta

    def resume_scan(self, scan_id: str) -> tuple[SoloScanWorker, dict[str, Any]] | None:
        """Resume unfinished solo work using the original profiles and solo settings."""
        scan_dir = self.config.scans_dir / scan_id
        scan_file, checkpoint_file = scan_dir / "scan.json", scan_dir / "checkpoint.json"
        if not scan_file.exists() or not checkpoint_file.exists():
            return None
        scan_meta = json.loads(scan_file.read_text(encoding="utf-8"))
        if scan_meta.get("scan_type") != "Solo Scan":
            return None
        checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        profiles = [p for pid in scan_meta.get("profile_ids", [])
                    if (p := self.profile_service.get_profile(pid)) is not None]
        worker = SoloScanWorker(
            scan_id=scan_id,
            files=discover_photos(scan_meta.get("sources", []), recursive=scan_meta.get("recursive", True)),
            profiles=profiles,
            output_dir=Path(scan_meta["output_dir"]),
            checkpoint_file=checkpoint_file,
            face_engine=self.face_engine,
            output_service=self.output_service,
            unknown_face_service=self.unknown_face_service,
            face_cache_service=self.face_cache_service,
            threshold=scan_meta.get("threshold", 70.0),
            performance_mode=scan_meta.get("performance_mode", "Maximum Performance"),
            operation_mode=scan_meta.get("operation_mode", "copy"),
            folder_organization=scan_meta.get("folder_organization", "flat"),
            all_system_profiles=self.profile_service.list_profiles(),
            allow_distant_photobombers=scan_meta.get("allow_distant_photobombers", False),
            min_sharpness=scan_meta.get("min_sharpness", 0.0),
            start_index=0,  # Completion order is not file order; processed_files is authoritative.
            initial_stats=checkpoint,
        )
        self.current_worker = worker
        self.active_scan_data = scan_meta
        worker.finished_signal.connect(self._on_worker_finished)
        return worker, scan_meta

    def verify_copied_photos(
        self, copied_file_pairs: list[tuple[str, str]]
    ) -> tuple[bool, int, list[str]]:
        """
        Verifies 100% of copied file pairs by content on disk.

        :return: (is_100_percent_verified, count_verified, list_of_verified_source_paths)
        """
        result, count, sources, self._verified_copies = verify_copy_pairs(copied_file_pairs)
        return result, count, sources

    def delete_verified_sources(self, source_paths: list[str]) -> tuple[int, int]:
        """
        Safely deletes verified original source files from disk after user confirmation (sends to Trash / Recycle Bin).

        :return: (successfully_deleted_count, error_count)
        """
        return trash_verified_sources(source_paths, self._verified_copies)

    def _on_worker_finished(self, summary: dict[str, Any]):
        """Handler called when SoloScanWorker finishes."""
        scan_id = summary.get("scan_id")
        if self.active_scan_data and self.active_scan_data.get("scan_id") == scan_id:
            record = self.active_scan_data.copy()
            record.update(summary)
            record["end_time"] = datetime.datetime.now().isoformat()

            s_dir = self.config.scans_dir / scan_id
            if s_dir.exists():
                with open(s_dir / "results.json", "w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2)

            self.history_service.record_scan(record)
