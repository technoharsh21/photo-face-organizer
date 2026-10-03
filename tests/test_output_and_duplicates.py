"""
Tests for Output Service, Safety Rules, Filename Collision, and Duplicate Detection.
"""

import tempfile
from pathlib import Path

from domain.duplicate_detector import DuplicateDetector
from services.output_service import OutputService


def test_copy_only_safety_and_filename_conflicts():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        index_file = tmp_path / "index.json"
        detector = DuplicateDetector(index_file)
        service = OutputService(detector)

        # Create original photo file
        src_file = tmp_path / "original.jpg"
        src_file.write_bytes(b"sample photo image data 123")

        dest_dir = tmp_path / "Output" / "Harsh"

        # First copy
        success1, target1, status1 = service.copy_photo_to_destination(src_file, dest_dir, "Harsh")
        assert success1 is True
        assert target1.name == "original.jpg"
        assert target1.exists()
        # Original file MUST remain unchanged
        assert src_file.exists()

        # Second copy of SAME file content to SAME destination -> Duplicate skipped
        success2, target2, status2 = service.copy_photo_to_destination(src_file, dest_dir, "Harsh")
        assert success2 is False
        assert status2 == "DUPLICATE_SKIPPED"

        # Third copy of DIFFERENT file content with SAME filename -> photo_1.jpg created
        src_file2 = tmp_path / "folder2" / "original.jpg"
        src_file2.parent.mkdir(parents=True, exist_ok=True)
        src_file2.write_bytes(b"different photo image content 456")

        success3, target3, status3 = service.copy_photo_to_destination(src_file2, dest_dir, "Harsh")
        assert success3 is True
        assert target3.name == "original_1.jpg"
        assert target3.exists()


def test_group_photo_routing_rules():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        detector = DuplicateDetector(tmp_path / "index.json")
        service = OutputService(detector)

        src_photo = tmp_path / "group.jpg"
        src_photo.write_bytes(b"group photo data")

        out_base = tmp_path / "Output"

        # 1. Multiple matched people (Harsh and John) -> copied to both folders once
        res = service.process_photo_output(src_photo, out_base, matched_profile_names={"Harsh", "John"})
        assert len(res) == 2
        assert (out_base / "Harsh" / "group.jpg").exists()
        assert (out_base / "John" / "group.jpg").exists()
        assert not (out_base / "No Match").exists()

        # 2. Zero matched people -> copied to No Match folder ONLY
        src_photo2 = tmp_path / "unmatched.jpg"
        src_photo2.write_bytes(b"unmatched photo data")
        res2 = service.process_photo_output(src_photo2, out_base, matched_profile_names=set())
        assert len(res2) == 1
        assert res2[0][0] == "No Match"
        assert (out_base / "No Match" / "unmatched.jpg").exists()


def test_duplicate_detector_caching_and_clear(tmp_path):
    detector = DuplicateDetector(tmp_path / "index.json")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    f1 = dest_dir / "pic1.jpg"
    content = b"hashed image content"
    f1.write_bytes(content)
    f_hash = detector.compute_file_hash(f1)

    # Initial check indexes the folder
    assert detector.is_duplicate(f_hash, dest_dir) is True
    assert detector.is_duplicate("non_existent_hash", dest_dir) is False

    # Register new hash directly
    detector.register_copy("new_fake_hash", dest_dir)
    assert detector.is_duplicate("new_fake_hash", dest_dir) is True

    # Clear cache
    detector.clear()
    assert len(detector._folder_hash_cache) == 0
    # Re-indexes on next check
    assert detector.is_duplicate(f_hash, dest_dir) is True


def test_exif_date_extraction_and_subfolder_generation(tmp_path):
    from PIL import Image

    detector = DuplicateDetector(tmp_path / "index.json")
    service = OutputService(detector)

    # 1. Create photo with EXIF DateTimeOriginal
    img_path = tmp_path / "vacation.jpg"
    img = Image.new("RGB", (64, 64), color="red")
    exif = img.getexif()
    exif[36867] = "2026:08:15 14:30:00"  # DateTimeOriginal
    img.save(img_path, exif=exif)

    extracted_dt = service.extract_photo_date(img_path)
    assert extracted_dt.year == 2026
    assert extracted_dt.month == 8
    assert extracted_dt.day == 15

    # Subfolder path tests
    assert service.build_date_subfolder(img_path, "flat") == Path("")
    assert service.build_date_subfolder(img_path, "year_date") == Path("2026/2026-08-15")
    assert service.build_date_subfolder(img_path, "year_month") == Path("2026/2026-08 (August)")
    assert service.build_date_subfolder(img_path, "year_only") == Path("2026")


def test_process_photo_output_with_date_organization(tmp_path):
    from PIL import Image

    detector = DuplicateDetector(tmp_path / "index.json")
    service = OutputService(detector)

    img_path = tmp_path / "birthday.jpg"
    img = Image.new("RGB", (64, 64), color="green")
    exif = img.getexif()
    exif[36867] = "2026:04:20 10:00:00"
    img.save(img_path, exif=exif)

    out_base = tmp_path / "Output"

    # Year / Date structure
    res = service.process_photo_output(
        img_path, out_base, matched_profile_names={"Alice"}, folder_organization="year_date"
    )
    assert len(res) == 1
    expected_target = out_base / "Alice" / "2026" / "2026-04-20" / "birthday.jpg"
    assert expected_target.exists()

    # Year / Month structure
    img_path2 = tmp_path / "event.jpg"
    img2 = Image.new("RGB", (64, 64), color="yellow")
    exif2 = img2.getexif()
    exif2[36867] = "2026:12:25 18:00:00"
    img2.save(img_path2, exif=exif2)

    res2 = service.process_photo_output(
        img_path2, out_base, matched_profile_names={"Bob"}, folder_organization="year_month"
    )
    assert len(res2) == 1
    expected_target2 = out_base / "Bob" / "2026" / "2026-12 (December)" / "event.jpg"
    assert expected_target2.exists()


def test_fallback_to_mtime_when_exif_missing(tmp_path):
    import os
    import time

    detector = DuplicateDetector(tmp_path / "index.json")
    service = OutputService(detector)

    plain_file = tmp_path / "no_exif.png"
    plain_file.write_bytes(b"dummy png without exif data")

    # Set custom mtime: 2025-06-10 12:00:00 UTC (1749556800)
    fake_timestamp = 1749556800.0
    os.utime(plain_file, (fake_timestamp, fake_timestamp))

    extracted_dt = service.extract_photo_date(plain_file)
    assert extracted_dt.year == 2025
    assert extracted_dt.month == 6
    assert extracted_dt.day == 10

    subfolder = service.build_date_subfolder(plain_file, "year_date")
    assert subfolder == Path("2025/2025-06-10")

