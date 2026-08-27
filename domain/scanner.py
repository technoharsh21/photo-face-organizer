"""
Scanner File Discovery Module.

Discovers, deduplicates, and validates source photos from files and directories.
Supports optional recursive directory scanning.
"""

from pathlib import Path

from domain.image_loader import is_supported_image


def discover_photos(sources: list[str], recursive: bool = True) -> list[Path]:
    """
    Given a list of source paths (files or directories), return a list of unique supported photo Paths.

    :param sources: List of file or folder path strings.
    :param recursive: Whether to recurse into subdirectories.
    :return: List of resolved unique Path objects.
    """
    discovered_files: list[Path] = []
    seen_paths: set[Path] = set()

    for source_str in sources:
        if not source_str:
            continue
        p = Path(source_str).resolve()
        if not p.exists():
            continue

        if p.is_file():
            if is_supported_image(p) and p not in seen_paths:
                seen_paths.add(p)
                discovered_files.append(p)
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for item in p.glob(pattern):
                if item.is_file() and is_supported_image(item):
                    resolved_item = item.resolve()
                    if resolved_item not in seen_paths:
                        seen_paths.add(resolved_item)
                        discovered_files.append(resolved_item)

    return discovered_files
