"""
Application settings storage.

Stores user preferences like home temple selection in a JSON file.

Author: Shrinivas Deshpande
Date: December 20, 2025
"""

import json
from pathlib import Path
from typing import Optional


class AppSettings:
    """Manage application settings with JSON file persistence."""

    def __init__(self, settings_file: str = "data/app_settings.json"):
        self.settings_file = Path(settings_file)
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self._settings = self._load()

    def _load(self) -> dict:
        """Load settings from JSON file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        """Save settings to JSON file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def get_home_temple_id(self) -> Optional[int]:
        """Get the saved home temple ID."""
        temple_id = self._settings.get("home_temple_id")
        return int(temple_id) if temple_id is not None else None

    def set_home_temple_id(self, temple_id: Optional[int]):
        """Set the home temple ID."""
        if temple_id is None:
            self._settings.pop("home_temple_id", None)
        else:
            self._settings["home_temple_id"] = temple_id
        self._save()

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value."""
        self._settings[key] = value
        self._save()
