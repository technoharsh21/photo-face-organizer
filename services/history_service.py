"""
History Service Module.

Records and queries historical scan runs stored locally in JSONL format.
Deleting history records removes local metadata only and NEVER deletes copied photos.
"""

import json
from typing import Any

from config import Config


class HistoryService:
    """Manages scan execution history persisted in JSONL format."""

    def __init__(self, config: Config):
        self.config = config
        self.history_file = config.history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def record_scan(self, scan_data: dict[str, Any]):
        """Append or update a scan history entry."""
        scans = self.get_all_scans()
        # Check if record already exists and update, otherwise append
        scan_id = scan_data.get("scan_id")
        updated = False
        for i, s in enumerate(scans):
            if s.get("scan_id") == scan_id:
                scans[i] = scan_data
                updated = True
                break

        if not updated:
            scans.append(scan_data)

        self._save_all_scans(scans)

    def get_all_scans(self) -> list[dict[str, Any]]:
        """Return list of all scan records sorted by start time (newest first)."""
        scans = []
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                scans.append(json.loads(line))
                            except Exception:
                                pass
            except Exception:
                pass
        scans.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return scans

    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Get scan record by ID."""
        for scan in self.get_all_scans():
            if scan.get("scan_id") == scan_id:
                return scan
        return None

    def delete_scan_record(self, scan_id: str) -> bool:
        """
        Deletes scan record from history.
        MANDATE: Deleting history NEVER deletes output photos.
        """
        scans = self.get_all_scans()
        new_scans = [s for s in scans if s.get("scan_id") != scan_id]
        if len(new_scans) < len(scans):
            self._save_all_scans(new_scans)
            return True
        return False

    def clear_all_history(self):
        """Clear all history metadata entries."""
        self._save_all_scans([])

    def _save_all_scans(self, scans: list[dict[str, Any]]):
        """Rewrite all scan records to JSONL file."""
        with open(self.history_file, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(s) + "\n" for s in scans)
