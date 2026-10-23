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


def test_exact_scan_skips_full_hash_for_different_prefixes_but_checks_matching_prefixes(tmp_path):
    service = DuplicateService(Config(app_data_dir=tmp_path / "appdata"))
    files = [tmp_path / f"{i}.jpg" for i in range(4)]
    for path, data in zip(files, (b"a" * 4096 + b"x", b"a" * 4096 + b"y",
                                   b"b" * 4096 + b"x", b"b" * 4096 + b"x")):
        path.write_bytes(data)

    with patch.object(service, "compute_file_hash", wraps=service.compute_file_hash) as hash_file:
        groups = service.scan_directories_for_duplicates([tmp_path])

    assert len(groups) == 1
    assert {f["path"] for f in groups[0]["files"]} == {str(files[2]), str(files[3])}
    assert hash_file.call_count == 4  # Same-prefix candidates still need full verification.


def test_exact_scan_skips_full_hash_when_same_size_prefixes_differ(tmp_path):
    service = DuplicateService(Config(app_data_dir=tmp_path / "appdata"))
    (tmp_path / "a.jpg").write_bytes(b"a" * 5000)
    (tmp_path / "b.jpg").write_bytes(b"b" * 5000)

    with patch.object(service, "compute_file_hash", wraps=service.compute_file_hash) as hash_file:
        assert service.scan_directories_for_duplicates([tmp_path]) == []
    hash_file.assert_not_called()


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
    assert service.scan_directories_for_duplicates([dir1]) == []


def test_quality_keeps_high_resolution_copy_even_when_older_is_smaller(tmp_path):
    from PIL import Image, ImageDraw

    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    large = Image.new("RGB", (160, 160), "white")
    ImageDraw.Draw(large).rectangle((20, 20, 100, 100), fill="blue")
    large.save(tmp_path / "photo (1).png")
    large.resize((80, 80)).save(tmp_path / "photo.png")

    groups = service.scan_directories_for_duplicates([tmp_path], method="visual")
    assert len(groups) == 1
    assert next(f for f in groups[0]["files"] if f["is_recommended_keep"])["filename"] == "photo (1).png"


def test_visual_scan_emits_completed_groups_and_can_stop(tmp_path):
    from PIL import Image, ImageDraw

    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    for prefix, color in (("first", "red"), ("second", "green")):
        image = Image.new("RGB", (100, 100), "white")
        ImageDraw.Draw(image).rectangle((20, 20, 70, 70), fill=color)
        for suffix in ("", "-copy"):
            image.save(tmp_path / f"{prefix}{suffix}.png")

    seen = []
    stopped = False

    def on_group(group):
        nonlocal stopped
        seen.append(group)
        stopped = True

    groups = service.scan_directories_for_duplicates([tmp_path], on_group=on_group,
                                                     cancel_check=lambda: stopped)
    assert len(groups) == len(seen) == 1
    assert {f["filename"] for f in groups[0]["files"]} == {"first.png", "first-copy.png"}


def test_exact_scan_preserves_completed_groups_when_stopped(tmp_path):
    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    for name, data in (("one.jpg", b"first"), ("one-copy.jpg", b"first"),
                       ("two.jpg", b"second"), ("two-copy.jpg", b"second")):
        (tmp_path / name).write_bytes(data)
    seen = []
    groups = service.scan_directories_for_duplicates(
        [tmp_path], method="exact", on_group=seen.append, cancel_check=lambda: bool(seen))
    assert len(groups) == len(seen) == 1
    assert groups[0]["files"] == seen[0]["files"]


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


def test_videos_are_found_in_both_modes_without_mixing_with_photos(tmp_path):
    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    selected = tmp_path / "selected"
    nested = selected / "nested"
    nested.mkdir(parents=True)
    first = selected / "clip.mp4"
    second = nested / "clip-copy.MOV"
    different = selected / "other.mp4"
    photo = selected / "image.jpg"
    photo_copy = selected / "image-copy.jpg"
    for p, content in ((first, b"video 1"), (second, b"video 1"),
                       (different, b"video 2"), (photo, b"video 1"), (photo_copy, b"video 1")):
        p.write_bytes(content)

    for mode in ("visual", "exact"):
        photos_only = service.scan_directories_for_duplicates([selected, nested], method=mode)
        assert len(photos_only) == 1
        assert {f["path"] for f in photos_only[0]["files"]} == {str(photo), str(photo_copy)}

        non_recursive = service.scan_directories_for_duplicates(
            [selected], recursive=False, method=mode, include_videos=True)
        assert len(non_recursive) == 1
        groups = service.scan_directories_for_duplicates(
            [selected, nested], recursive=True, method=mode, include_videos=True)
        assert len(groups) == 2
        video_group = next(group for group in groups if group["set_id"] == "video_set_1")
        assert {f["path"] for f in video_group["files"]} == {str(first), str(second)}
        assert video_group["potential_savings"] == len(b"video 1")


def test_video_scan_does_not_follow_links_outside_selected_folder(tmp_path):
    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    selected = tmp_path / "selected"
    selected.mkdir()
    (selected / "inside.mp4").write_bytes(b"same video")
    outside = tmp_path / "outside.mov"
    outside.write_bytes(b"same video")
    (selected / "linked.mov").symlink_to(outside)

    assert service.scan_directories_for_duplicates([selected], method="exact", include_videos=True) == []
