"""
Unit tests for domain.image_loader, including HEIC/HEIF and RAW format handling.
"""

import tempfile
from pathlib import Path
from PIL import Image
import pillow_heif
import pytest

from domain.image_loader import load_image, is_supported_image, _HEIF_AVAILABLE, _RAWPY_AVAILABLE


def test_is_supported_image():
    assert is_supported_image(Path("test.jpg")) is True
    assert is_supported_image(Path("test.jpeg")) is True
    assert is_supported_image(Path("test.png")) is True
    assert is_supported_image(Path("test.webp")) is True
    assert is_supported_image(Path("test.heic")) is True
    assert is_supported_image(Path("test.HEIF")) is True
    assert is_supported_image(Path("test.arw")) is True
    assert is_supported_image(Path("test.txt")) is False
    assert is_supported_image(Path("test.mp4")) is False


def test_load_standard_image():
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = Path(tmp_dir) / "test.png"
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(img_path)

        loaded, err = load_image(img_path)
        assert err is None
        assert loaded is not None
        assert loaded.size == (100, 100)
        assert loaded.mode == "RGB"


def test_load_heic_image():
    assert _HEIF_AVAILABLE is True
    with tempfile.TemporaryDirectory() as tmp_dir:
        heic_path = Path(tmp_dir) / "test.heic"
        
        # Create a sample image and save as HEIF/HEIC
        img = Image.new("RGB", (64, 64), color=(0, 128, 255))
        img.save(heic_path, format="HEIF")

        loaded, err = load_image(heic_path)
        assert err is None
        assert loaded is not None
        assert loaded.size == (64, 64)
        assert loaded.mode == "RGB"


def test_load_nonexistent_file():
    loaded, err = load_image(Path("non_existent_file_12345.jpg"))
    assert loaded is None
    assert "File not found" in err
