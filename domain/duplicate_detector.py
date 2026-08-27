"""
Duplicate Detector Module.

Uses SHA-256 file hashing to verify if an identical photo file already exists
inside the destination output folder on disk.
Prevents creating redundant duplicate copies of the same photo in the same target directory.
"""

import hashlib
from pathlib import Path


class DuplicateDetector:
    """
    Checks if a file with matching SHA-256 hash exists inside the destination output folder.
    """

    def __init__(self, index_file_path: Path):
        self.index_file_path = Path(index_file_path)

    @staticmethod
    def compute_file_hash(file_path: Path, block_size: int = 65536) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def is_duplicate(self, file_hash: str, destination_folder: Path) -> bool:
        """
        Check if destination_folder on disk already contains a file with matching SHA-256 hash.
        """
        dest_path = Path(destination_folder)
        if not dest_path.exists() or not dest_path.is_dir():
            return False

        for existing in dest_path.iterdir():
            if existing.is_file():
                try:
                    if self.compute_file_hash(existing) == file_hash:
                        return True
                except Exception:
                    pass

        return False

    def register_copy(self, file_hash: str, destination_folder: Path):
        """No-op for disk-based verification."""
        pass

    def clear(self):
        """No-op."""
        pass
