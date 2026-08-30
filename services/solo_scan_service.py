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

        # 1. Discover photo files
        discovered_paths = discover_photos(sources, recursive=recursive)

        # 2. Fetch selected profiles
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
            "threshold": threshold,
            "allow_distant_photobombers": allow_distant_photobombers,
            "min_sharpness": min_sharpness,
            "total_files": len(discovered_paths),
        }

        # Save scan.json
        with open(scan_dir / "scan.json", "w", encoding="utf-8") as f:
            json.dump(scan_meta, f, indent=2)

        checkpoint_file = scan_dir / "checkpoint.json"

        all_sys_profiles = self.profile_service.list_profiles()

        # Create Worker Thread
        worker = SoloScanWorker(
            scan_id=scan_id,
            files=discovered_paths,
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
            start_index=0,
            all_system_profiles=all_sys_profiles,
            allow_distant_photobombers=allow_distant_photobombers,
            min_sharpness=min_sharpness,
        )

        self.current_worker = worker
        self.active_scan_data = scan_meta

        worker.finished_signal.connect(self._on_worker_finished)
        return worker, scan_meta

    def verify_copied_photos(
        self, copied_file_pairs: list[tuple[str, str]]
    ) -> tuple[bool, int, list[str]]:
        """
        Verifies 100% of copied file pairs on disk.

        Checks:
        1. Target file exists.
        2. Target file size > 0.
        3. Target file size == Source file size.

        :return: (is_100_percent_verified, count_verified, list_of_verified_source_paths)
        """
        if not copied_file_pairs:
            return True, 0, []

        verified_sources: set[str] = set()
        failed_count = 0

        for src_str, target_str in copied_file_pairs:
            src = Path(src_str)
            tgt = Path(target_str)

            if not tgt.exists():
                logger.warning(f"Verification failed: Target file missing: {target_str}")
                failed_count += 1
                continue

            try:
                tgt_size = tgt.stat().st_size
                src_size = src.stat().st_size if src.exists() else -1

                if tgt_size == 0 or tgt_size != src_size:
                    logger.warning(f"Verification failed: Size mismatch for {src_str} ({src_size} vs {tgt_size})")
                    failed_count += 1
                else:
                    verified_sources.add(str(src))
            except Exception as e:
                logger.warning(f"Verification check exception for {src_str}: {e}")
                failed_count += 1

        if failed_count == 0:
            return True, len(verified_sources), list(verified_sources)
        else:
            return False, failed_count, []

    def delete_verified_sources(self, source_paths: list[str]) -> tuple[int, int]:
        """
        Safely deletes verified original source files from disk after user confirmation.

        :return: (successfully_deleted_count, error_count)
        """
        deleted_count = 0
        error_count = 0

        for src_str in source_paths:
            src = Path(src_str)
            if src.exists():
                try:
                    src.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete source file {src_str}: {e}")
                    error_count += 1

        return deleted_count, error_count

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
