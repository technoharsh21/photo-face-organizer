"""
Unit tests for Duplicate Service.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

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


def test_remove_duplicates_trash_and_delete(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "folder1"
    dir1.mkdir()

    f1 = dir1 / "a.jpg"
    data = b"duplicate bytes 12345"
    f1.write_bytes(data)

    # Test delete
    f3 = dir1 / "c.jpg"
    f3.write_bytes(data)
    succ_del, err_del, freed_del = service.remove_duplicates([str(f3)], mode="delete")
    assert succ_del == 1
    assert not f3.exists()

    # Test trash (with mocked send_to_trash)
    f4 = dir1 / "d.jpg"
    f4.write_bytes(data)
    with patch("services.duplicate_service.send_to_trash", return_value=True) as mock_trash:
        succ_trash, err_trash, freed_trash = service.remove_duplicates([str(f4)], mode="trash")
        assert succ_trash == 1
        assert err_trash == 0
        assert freed_trash == len(data)
        mock_trash.assert_called_once()


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024 * 500) == "500.0 KB"
    assert format_bytes(1024 * 1024 * 5) == "5.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.00 GB"


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


def test_oldest_original_selection_with_multiple_copies(tmp_path):
    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "photos"
    dir1.mkdir()

    content = b"exact byte identical photo data 9999"
    # Create original file
    orig = dir1 / "IMG_2026.JPG"
    orig.write_bytes(content)

    # Create 10 copies with typical OS copy suffixes
    copies = []
    for i in range(1, 11):
        cp = dir1 / f"IMG_2026 - Copy ({i}).JPG" if i > 1 else dir1 / "IMG_2026 - Copy.JPG"
        cp.write_bytes(content)
        copies.append(cp)

    sets = service.scan_directories_for_duplicates([dir1], recursive=True)
    assert len(sets) == 1
    dset = sets[0]
    assert dset["file_count"] == 11

    # Apply keep_oldest rule
    service.apply_auto_select_rule(sets, rule="keep_oldest")
    files = dset["files"]

    # The clean original MUST be kept
    kept = [f for f in files if f["is_recommended_keep"]]
    assert len(kept) == 1
    assert kept[0]["filename"] == "IMG_2026.JPG"

    # All 10 copies MUST be marked for removal
    for f in files:
        if f["filename"] != "IMG_2026.JPG":
            assert f["is_selected_for_removal"] is True
            assert f["is_recommended_keep"] is False


def test_mobile_and_recompressed_duplicate_detection(tmp_path):
    from PIL import Image, ImageDraw

    config = Config(app_data_dir=tmp_path / "appdata")
    service = DuplicateService(config)

    dir1 = tmp_path / "photos"
    dir1.mkdir()

    # Create original photo with pattern
    p1 = dir1 / "photo.jpg"
    img1 = Image.new("RGB", (120, 120), (180, 80, 40))
    d1 = ImageDraw.Draw(img1)
    d1.rectangle([20, 20, 60, 60], fill=(0, 200, 255))
    d1.line([0, 0, 120, 120], fill=(255, 255, 255), width=2)
    img1.save(p1, "JPEG", quality=95)

    # Create mobile copy with (1) suffix, recompressed and with custom EXIF tags
    p2 = dir1 / "photo (1).jpg"
    exif = img1.getexif()
    exif[306] = "2026:10:15 21:00:00"
    exif[271] = "MobileDevice"
    exif[272] = "PhoneModel"
    img1.save(p2, "JPEG", quality=80, exif=exif)

    # Ensure their byte sizes are different (as happens on mobile)
    assert p1.stat().st_size != p2.stat().st_size

    # Create a completely different photo
    p3 = dir1 / "unrelated.jpg"
    img3 = Image.new("RGB", (120, 120), (30, 180, 70))
    d3 = ImageDraw.Draw(img3)
    d3.ellipse([30, 30, 90, 90], fill=(255, 0, 100))
    img3.save(p3, "JPEG", quality=90)

    # 1. Visual mode (default) MUST detect photo.jpg and photo (1).jpg as duplicates
    sets = service.scan_directories_for_duplicates([dir1], recursive=True, method="visual")
    assert len(sets) == 1
    dset = sets[0]
    assert dset["file_count"] == 2
    filenames = [f["filename"] for f in dset["files"]]
    assert "photo.jpg" in filenames
    assert "photo (1).jpg" in filenames
    assert "unrelated.jpg" not in filenames

    # Auto-selection rule: clean original photo.jpg MUST be kept, photo (1).jpg marked for removal
    kept = [f for f in dset["files"] if f["is_recommended_keep"]]
    assert len(kept) == 1
    assert kept[0]["filename"] == "photo.jpg"

    removed = [f for f in dset["files"] if f["is_selected_for_removal"]]
    assert len(removed) == 1
    assert removed[0]["filename"] == "photo (1).jpg"

    # 2. Exact mode should NOT detect them because sizes and byte hashes differ
    sets_exact = service.scan_directories_for_duplicates([dir1], recursive=True, method="exact")
    assert len(sets_exact) == 0


def test_visual_scan_does_not_merge_different_flat_colors(tmp_path):
    from PIL import Image

    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    Image.new("RGB", (100, 100), (100, 100, 100)).save(tmp_path / "gray1.png")
    Image.new("RGB", (100, 100), (110, 110, 110)).save(tmp_path / "gray2.png")

    assert service.scan_directories_for_duplicates([tmp_path], method="visual") == []


def test_visual_groups_require_every_pair_to_match(tmp_path):
    import numpy as np

    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    files = [tmp_path / f"{name}.jpg" for name in ("a", "b", "c")]
    for i, path in enumerate(files):
        path.write_bytes(bytes([i + 1]))

    # A-B and B-C pass distance 2, but A-C fails distance 4.
    thumb = np.arange(192, dtype=np.uint8).reshape(8, 8, 3)
    hashes = dict(zip(files, (0, 3, 15)))
    with patch.object(service, "compute_perceptual_hash", side_effect=lambda p: (hashes[p], 1.0, thumb)):
        groups = service.scan_directories_for_duplicates([tmp_path], method="visual", max_distance=2)

    assert len(groups) == 1
    assert groups[0]["file_count"] == 2


def test_cleanup_rechecks_both_duplicate_and_keeper(tmp_path):
    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    keeper = tmp_path / "keep.jpg"
    duplicate = tmp_path / "copy.jpg"
    keeper.write_bytes(b"original")
    duplicate.write_bytes(b"original")
    expected = {str(p): service.compute_file_hash(p) for p in (keeper, duplicate)}
    keepers = {str(duplicate): str(keeper)}

    duplicate.write_bytes(b"replacement")
    assert service.remove_duplicates([str(duplicate)], mode="delete", expected_hashes=expected,
                                     keepers_by_path=keepers) == (0, 1, 0)
    assert duplicate.read_bytes() == b"replacement"

    duplicate.write_bytes(b"original")
    keeper.write_bytes(b"changed keeper")
    assert service.remove_duplicates([str(duplicate)], mode="delete", expected_hashes=expected,
                                     keepers_by_path=keepers) == (0, 1, 0)
    assert duplicate.exists()

    keeper.write_bytes(b"original")
    assert service.remove_duplicates([str(duplicate)], mode="delete", expected_hashes=expected,
                                     keepers_by_path=keepers) == (1, 0, len(b"original"))
    assert not duplicate.exists()
