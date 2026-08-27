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
