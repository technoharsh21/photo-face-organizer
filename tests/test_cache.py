"""
Unit tests for Persistent Face Cache Service.
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from config import Config
from services.face_cache_service import FaceCacheService
from services.settings_service import SettingsService


def test_face_cache_service_crud():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = Config(app_data_dir=tmp_path)
        settings = SettingsService(config)
        cache_svc = FaceCacheService(config, settings)

        # Create dummy file
        dummy_file = tmp_path / "photo.jpg"
        dummy_file.write_bytes(b"dummy image data 12345")

        # Initially no cache
        assert cache_svc.get_cached_faces(dummy_file) is None

        # Save cache entry
        locs = [(10, 50, 60, 10)]
        encs = [np.ones(512, dtype=np.float64)]

        cache_svc.save_cached_faces(dummy_file, locs, encs)

        # Retrieve cache entry
        cached = cache_svc.get_cached_faces(dummy_file)
        assert cached is not None
        cached_locs, cached_encs = cached
        assert len(cached_locs) == 1
        assert cached_locs[0] == (10, 50, 60, 10)
        assert len(cached_encs) == 1
        assert np.array_equal(cached_encs[0], encs[0])

        # Test clear cache
        deleted_count, freed_mb = cache_svc.clear_cache()
        assert deleted_count == 1
        assert cache_svc.get_cached_faces(dummy_file) is None


def test_face_cache_toggle_setting():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = Config(app_data_dir=tmp_path)
        settings = SettingsService(config)
        cache_svc = FaceCacheService(config, settings)

        dummy_file = tmp_path / "photo2.jpg"
        dummy_file.write_bytes(b"dummy image data 67890")

        # Disable cache in settings
        settings.update({"enable_face_cache": False})
        assert cache_svc.is_enabled() is False

        cache_svc.save_cached_faces(dummy_file, [(0, 10, 10, 0)], [np.zeros(128)])
        assert cache_svc.get_cached_faces(dummy_file) is None
