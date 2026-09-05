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
    Strictly scans selected folders and their subdirectories (when recursive=True).
    Never scans outside selected folders or parent directories.
    """
    import os

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
            if recursive:
                for root, _, files in os.walk(str(p), followlinks=False):
                    root_path = Path(root).resolve()
                    try:
                        root_path.relative_to(p)
                    except ValueError:
                        continue

                    for fname in files:
                        fpath = root_path / fname
                        if is_supported_image(fpath):
                            resolved_item = fpath.resolve()
                            try:
                                resolved_item.relative_to(p)
                                if resolved_item not in seen_paths:
                                    seen_paths.add(resolved_item)
                                    discovered_files.append(resolved_item)
                            except ValueError:
                                pass
            else:
                try:
                    for item in p.iterdir():
                        if item.is_file() and is_supported_image(item):
                            resolved_item = item.resolve()
                            if resolved_item.parent == p and resolved_item not in seen_paths:
                                seen_paths.add(resolved_item)
                                discovered_files.append(resolved_item)
                except Exception:
                    pass

    return discovered_files
