"""
Unit tests for Duplicate Service.
"""

import tempfile
from pathlib import Path

from config import Config
from services.duplicate_service import DuplicateService, format_bytes


def test_duplicate_detection_and_grouping(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "folder1"
    dir1.mkdir()

    # Create 2 byte-identical files
    file1 = dir1 / "image1.jpg"
    file2 = dir1 / "image2.jpg"
    content_a = b"exact byte identical photo image content 12345"
    file1.write_bytes(content_a)
    file2.write_bytes(content_a)

    # Create 1 unique file
    file3 = dir1 / "image3.jpg"
    file3.write_bytes(b"unique photo image content 67890")

    sets = service.scan_directories_for_duplicates([dir1], recursive=True)

    assert len(sets) == 1
    dset = sets[0]
    assert dset["file_count"] == 2
    assert dset["sample_name"] in ["image1.jpg", "image2.jpg"]
    assert dset["potential_savings"] == len(content_a)


def test_auto_select_rules(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "folder1"
    dir1.mkdir()

    f1 = dir1 / "old.jpg"
    f2 = dir1 / "new.jpg"
    content = b"identical bytes"
    f1.write_bytes(content)
    f2.write_bytes(content)

    sets = service.scan_directories_for_duplicates([dir1], recursive=True)
    assert len(sets) == 1

    # Apply keep_oldest
    service.apply_auto_select_rule(sets, rule="keep_oldest")
    files = sets[0]["files"]
    assert files[0]["is_recommended_keep"] is True
    assert files[1]["is_selected_for_removal"] is True

    # Apply keep_newest
    service.apply_auto_select_rule(sets, rule="keep_newest")
    files_newest = sets[0]["files"]
    assert files_newest[0]["is_recommended_keep"] is True


def test_remove_duplicates_quarantine_and_delete(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "folder1"
    dir1.mkdir()

    f1 = dir1 / "a.jpg"
    f2 = dir1 / "b.jpg"
    data = b"duplicate bytes 12345"
    f1.write_bytes(data)
    f2.write_bytes(data)

    # Test quarantine
    success, err, freed = service.remove_duplicates([str(f2)], mode="quarantine")
    assert success == 1
    assert err == 0
    assert freed == len(data)
    assert not f2.exists()
    assert (service.quarantine_dir / "b.jpg").exists()

    # Test delete
    f3 = dir1 / "c.jpg"
    f3.write_bytes(data)
    succ_del, err_del, freed_del = service.remove_duplicates([str(f3)], mode="delete")
    assert succ_del == 1
    assert not f3.exists()


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024 * 500) == "500.0 KB"
    assert format_bytes(1024 * 1024 * 5) == "5.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.00 GB"


def test_quarantine_filename_collision(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "folder1"
    dir2 = tmp_path / "folder2"
    dir1.mkdir()
    dir2.mkdir()

    # Create two different files with identical filenames in different folders
    f1 = dir1 / "same_name.jpg"
    f2 = dir2 / "same_name.jpg"
    f1.write_bytes(b"content 1")
    f2.write_bytes(b"content 2")

    # Quarantine both
    succ1, _, _ = service.remove_duplicates([str(f1)], mode="quarantine")
    succ2, _, _ = service.remove_duplicates([str(f2)], mode="quarantine")

    assert succ1 == 1
    assert succ2 == 1
    # Both files must exist in quarantine without overwriting each other
    quarantine_files = list(service.quarantine_dir.glob("same_name*"))
    assert len(quarantine_files) == 2


def test_duplicate_scan_strict_parent_and_subfolder_isolation(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    # Hierarchy:
    # parent_dir/
    #   ├── parent_dup.jpg (same content as sub_dup.jpg)
    #   └── sub_dir/
    #       ├── sub_dup1.jpg (same content)
    #       ├── sub_dup2.jpg (same content)
    #       └── nested_dir/
    #           └── nested_dup.jpg (same content)

    parent_dir = tmp_path / "parent_dir"
    sub_dir = parent_dir / "sub_dir"
    nested_dir = sub_dir / "nested_dir"
    nested_dir.mkdir(parents=True)

    dup_bytes = b"duplicate photo byte content across levels"
    parent_file = parent_dir / "parent_dup.jpg"
    parent_file.write_bytes(dup_bytes)

    sub_f1 = sub_dir / "sub_dup1.jpg"
    sub_f2 = sub_dir / "sub_dup2.jpg"
    sub_f1.write_bytes(dup_bytes)
    sub_f2.write_bytes(dup_bytes)

    nested_file = nested_dir / "nested_dup.jpg"
    nested_file.write_bytes(dup_bytes)

    # 1. Non-recursive scan of sub_dir ONLY:
    # Must only find sub_dup1.jpg and sub_dup2.jpg.
    # Must NEVER include parent_dup.jpg or nested_dup.jpg!
    sets_non_rec = service.scan_directories_for_duplicates([sub_dir], recursive=False)
    assert len(sets_non_rec) == 1
    files_non_rec = [f["path"] for f in sets_non_rec[0]["files"]]
    assert len(files_non_rec) == 2
    assert str(sub_f1) in files_non_rec
    assert str(sub_f2) in files_non_rec
    assert str(parent_file) not in files_non_rec
    assert str(nested_file) not in files_non_rec

    # 2. Recursive scan of sub_dir:
    # Must include sub_dup1.jpg, sub_dup2.jpg, and nested_dup.jpg.
    # Must NEVER include parent_dup.jpg!
    sets_rec = service.scan_directories_for_duplicates([sub_dir], recursive=True)
    assert len(sets_rec) == 1
    files_rec = [f["path"] for f in sets_rec[0]["files"]]
    assert len(files_rec) == 3
    assert str(sub_f1) in files_rec
    assert str(sub_f2) in files_rec
    assert str(nested_file) in files_rec
    assert str(parent_file) not in files_rec


