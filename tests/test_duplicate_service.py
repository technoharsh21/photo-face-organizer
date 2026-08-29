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
