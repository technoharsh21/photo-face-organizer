"""
Configuration Module for Photo Face Organizer.

Defines default settings, application data paths, performance modes, device preferences, and matching rules.
"""

import os
import sys
from pathlib import Path

# Base Application Directory
APP_NAME = "PhotoFaceOrganizer"

def get_default_app_data_dir() -> Path:
    """Return platform-appropriate default application data directory."""
    if sys.platform == "win32":
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_NAME

DEFAULT_APP_DATA_DIR = get_default_app_data_dir()

class Config:
    """Central configuration class."""
    
    def __init__(self, app_data_dir: Path = DEFAULT_APP_DATA_DIR):
        self.app_data_dir = Path(app_data_dir)
        self.profiles_dir = self.app_data_dir / "profiles"
        self.scans_dir = self.app_data_dir / "scans"
        self.unknown_faces_dir = self.app_data_dir / "unknown_faces"
        self.duplicates_dir = self.app_data_dir / "duplicates"
        self.settings_dir = self.app_data_dir / "settings"
        self.history_dir = self.app_data_dir / "history"
        self.cache_dir = self.app_data_dir / "cache"
        
        self.ensure_directories()
        
    def ensure_directories(self):
        """Ensure all required application data subdirectories exist."""
        for d in [
            self.app_data_dir,
            self.profiles_dir,
            self.scans_dir,
            self.unknown_faces_dir,
            self.duplicates_dir,
            self.settings_dir,
            self.history_dir,
            self.cache_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)
            
    @property
    def duplicate_index_file(self) -> Path:
        return self.duplicates_dir / "index.json"

    @property
    def settings_file(self) -> Path:
        return self.settings_dir / "settings.json"

    @property
    def history_file(self) -> Path:
        return self.history_dir / "scans.jsonl"
