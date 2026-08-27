"""
Output Service Module.

Handles safe photo copying, output directory structure generation, filename conflict resolution,
and duplicate prevention via SHA-256 content hashing.

SAFETY MANDATE:
- COPY ONLY using shutil.copy2().
- NEVER move, delete, rename, or modify original source files.
"""

import shutil
from pathlib import Path

from domain.duplicate_detector import DuplicateDetector


class OutputService:
    """Manages output photo placement, filename collision resolution, and duplicate checks."""

    def __init__(self, duplicate_detector: DuplicateDetector):
        self.duplicate_detector = duplicate_detector

    @staticmethod
    def get_non_conflicting_path(target_folder: Path, original_filename: str) -> Path:
        """
        Generate a target path in target_folder that does not conflict with existing files.
        Preserves original file extension.
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

    def copy_photo_to_destination(
        self, source_path: Path, destination_folder: Path, folder_key: str
    ) -> tuple[bool, Path | None, str]:
        """
        Safely copy source_path to destination_folder.

        :param source_path: Original file path.
        :param destination_folder: Target directory path (e.g. Output/Harsh).
        :param folder_key: Key name identifying destination (e.g. 'Harsh' or 'No Match').
        :return: (copied_boolean, target_path_if_copied, status_message)
        """
        if not source_path.exists():
            return False, None, f"Source file does not exist: {source_path}"

        # 1. Compute file hash for duplicate detection
        file_hash = self.duplicate_detector.compute_file_hash(source_path)

        # 2. Check duplicate index per destination folder path
        if self.duplicate_detector.is_duplicate(file_hash, destination_folder):
            return False, None, "DUPLICATE_SKIPPED"

        # 3. Resolve filename collisions
        target_path = self.get_non_conflicting_path(destination_folder, source_path.name)

        # 4. Copy file using shutil.copy2 to preserve metadata, without altering original
        try:
            shutil.copy2(source_path, target_path)
            # Register in duplicate index
            self.duplicate_detector.register_copy(file_hash, destination_folder)
            return True, target_path, "COPIED"
        except Exception as e:
            return False, None, f"Copy error: {e!s}"

    @staticmethod
    def sanitize_folder_name(name: str) -> str:
        """Sanitize folder names to prevent invalid path characters or subfolder splits."""
        invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        clean_name = name.strip()
        for char in invalid_chars:
            clean_name = clean_name.replace(char, "_")
        return clean_name or "Unnamed_Folder"

    def process_photo_output(
        self,
        source_path: Path,
        output_base_dir: Path,
        matched_profile_names: set[str],
    ) -> list[tuple[str, Path | None, str]]:
        """
        Routes photo copy based on matched profiles.

        Rules:
        - If matched_profile_names is non-empty: copy photo to each matched person's folder once.
        - If matched_profile_names is empty: copy photo to 'No Match' folder.
        """
        results = []

        if matched_profile_names:
            # Copy into each unique matched person's folder
            for person_name in sorted(matched_profile_names):
                clean_name = self.sanitize_folder_name(person_name)
                person_folder = output_base_dir / clean_name
                success, target_path, status = self.copy_photo_to_destination(
                    source_path, person_folder, folder_key=clean_name
                )
                results.append((clean_name, target_path, status))
        else:
            # No profiles matched -> Copy to No Match folder
            no_match_folder = output_base_dir / "No Match"
            success, target_path, status = self.copy_photo_to_destination(
                source_path, no_match_folder, folder_key="No Match"
            )
            results.append(("No Match", target_path, status))

        return results
