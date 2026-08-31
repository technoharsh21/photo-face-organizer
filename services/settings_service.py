"""
Settings Service.

Manages application settings, device preferences, performance modes, matching thresholds,
and persists them locally in JSON.
"""

import json
import os
import tempfile
from typing import Any

from config import Config

DEFAULT_SETTINGS: dict[str, Any] = {
    "device_preference": "Auto",           # "Auto", "CPU", "GPU"
    "performance_mode": "Maximum Performance", # "Eco", "Balanced", "Maximum Performance"
    "matching_threshold": 50.0,            # Match score threshold (0 - 100)
    "recursive_scan": True,                # Default recursive directory scan
    "auto_group_unknowns": True,           # Group similar unknown faces automatically
}


class SettingsService:
    """Service to load, modify, and save user settings."""

    def __init__(self, config: Config):
        self.config = config
        self.settings_file = config.settings_file
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        """Load settings from JSON file if available."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception:
                self.settings = DEFAULT_SETTINGS.copy()
        else:
            self.save_settings()

    def save_settings(self):
        """Save current settings to JSON file atomically."""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self.settings, indent=2)
        dir_path = self.settings_file.parent
        fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(self.settings_file))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save_settings()

    def update(self, new_settings: dict[str, Any]):
        self.settings.update(new_settings)
        self.save_settings()

    def reset_to_defaults(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.save_settings()
