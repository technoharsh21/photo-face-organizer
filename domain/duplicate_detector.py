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
    Maintains an in-memory hash cache per destination folder for fast O(1) duplicate lookups.
    """

    def __init__(self, index_file_path: Path):
        self.index_file_path = Path(index_file_path)
        self._folder_hash_cache: dict[Path, set[str]] = {}

    @staticmethod
    def compute_file_hash(file_path: Path, block_size: int = 65536) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(block_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _ensure_folder_indexed(self, destination_folder: Path):
        """Index all existing files in destination_folder once."""
        dest_path = Path(destination_folder).resolve()
        if dest_path not in self._folder_hash_cache:
            hashes: set[str] = set()
            if dest_path.exists() and dest_path.is_dir():
                for existing in dest_path.iterdir():
                    if existing.is_file():
                        try:
                            hashes.add(self.compute_file_hash(existing))
                        except Exception:
                            pass
            self._folder_hash_cache[dest_path] = hashes

    def is_duplicate(self, file_hash: str, destination_folder: Path) -> bool:
        """
        Check if destination_folder on disk already contains a file with matching SHA-256 hash.
        Fast O(1) check using indexed cache.
        """
        dest_path = Path(destination_folder).resolve()
        self._ensure_folder_indexed(dest_path)
        return file_hash in self._folder_hash_cache.get(dest_path, set())

    def register_copy(self, file_hash: str, destination_folder: Path):
        """Register a newly copied file's hash in destination folder cache."""
        dest_path = Path(destination_folder).resolve()
        self._ensure_folder_indexed(dest_path)
        self._folder_hash_cache.setdefault(dest_path, set()).add(file_hash)

    def clear(self):
        """Clear in-memory folder hash cache."""
        self._folder_hash_cache.clear()
