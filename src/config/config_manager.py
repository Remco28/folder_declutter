"""
Configuration Manager for Desktop Sorter
Handles loading, saving, and updating configuration to persistent storage
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from .defaults import CURRENT_VERSION, default_config

logger = logging.getLogger(__name__)


class ConfigManager:
    """Configuration manager with static methods for config operations"""

    @staticmethod
    def get_appdata_dir(app_name: str = "DesktopSorter") -> Path:
        """
        Get platform-appropriate application data directory

        Args:
            app_name: Application name for directory

        Returns:
            Path to application data directory
        """
        if sys.platform == "win32":
            # Windows: %APPDATA%/DesktopSorter
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / app_name
            else:
                # Fallback if APPDATA not set
                return Path.home() / "AppData" / "Roaming" / app_name
        else:
            # Unix-like systems: ~/.config/DesktopSorter
            config_home = os.environ.get("XDG_CONFIG_HOME")
            if config_home:
                return Path(config_home) / app_name
            else:
                return Path.home() / ".config" / app_name

    @staticmethod
    def get_config_path() -> Path:
        """
        Get path to config.json file

        Returns:
            Path to configuration file
        """
        return ConfigManager.get_appdata_dir() / "config.json"

    @staticmethod
    def get_logs_dir() -> Path:
        """Return the directory where application logs should be stored."""
        return ConfigManager.get_appdata_dir() / "logs"

    @staticmethod
    def get_backups_root() -> Path:
        """Return the root directory for session backup archives."""
        return ConfigManager.get_appdata_dir() / "backups"

    @staticmethod
    def load() -> dict:
        """
        Load configuration from file or return defaults

        Returns:
            dict: Configuration data
        """
        config_path = ConfigManager.get_config_path()

        if not config_path.exists():
            logger.info(f"Config file not found at {config_path}, using defaults")
            return default_config()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Migrate if needed
            data = ConfigManager.migrate(data)

            # Normalize sections to exactly 6 entries by id
            normalized = default_config()
            for section in data.get("sections", []):
                section_id = section.get("id")
                if isinstance(section_id, int) and 0 <= section_id < 6:
                    normalized["sections"][section_id].update({
                        "label": section.get("label"),
                        "path": section.get("path"),
                        "kind": section.get("kind", "folder")
                    })

            logger.info(f"Config loaded successfully from {config_path}")
            return normalized

        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")
            return default_config()

    @staticmethod
    def save(config: dict) -> None:
        """
        Save configuration to file atomically

        Args:
            config: Configuration data to save
        """
        config_path = ConfigManager.get_config_path()

        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            temp_path = config_path.with_suffix(config_path.suffix + ".tmp")

            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Atomically replace the original file
            temp_path.replace(config_path)

            logger.debug(f"Config saved successfully to {config_path}")

        except (OSError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save config to {config_path}: {e}")

    @staticmethod
    def update_section(config: dict, section_id: int, *, label: Optional[str], path: Optional[str]) -> dict:
        """
        Update a section in the configuration

        Args:
            config: Configuration data to modify
            section_id: Section ID (0-5)
            label: Section label (None to clear)
            path: Section path (None to clear)

        Returns:
            dict: Updated configuration (same object, modified in place)
        """
        if not (0 <= section_id < 6):
            logger.warning(f"Invalid section_id: {section_id}. Must be 0-5.")
            return config

        # Ensure sections list exists and has correct length
        if "sections" not in config:
            config["sections"] = default_config()["sections"]

        while len(config["sections"]) <= section_id:
            config["sections"].append({
                "id": len(config["sections"]),
                "label": None,
                "kind": "folder",
                "path": None
            })

        # Update the section
        section = config["sections"][section_id]
        section["id"] = section_id
        section["label"] = label
        section["path"] = path
        section["kind"] = "folder"  # Only folder type in Phase 4

        logger.debug(f"Updated section {section_id}: label={label}, path={path}")
        return config

    @staticmethod
    def clear_section(config: dict, section_id: int) -> dict:
        """
        Clear a section (set label and path to None)

        Args:
            config: Configuration data to modify
            section_id: Section ID (0-5)

        Returns:
            dict: Updated configuration (same object, modified in place)
        """
        return ConfigManager.update_section(config, section_id, label=None, path=None)

    @staticmethod
    def migrate(config: dict) -> dict:
        """
        Migrate configuration to current version

        Args:
            config: Configuration data to migrate

        Returns:
            dict: Migrated configuration (same object, modified in place)
        """
        config_version = config.get("version", 0)

        if config_version < CURRENT_VERSION:
            logger.info(f"Migrating config from version {config_version} to {CURRENT_VERSION}")

            # Future migration logic would go here
            # For now, just ensure required fields exist
            if "sections" not in config:
                config["sections"] = default_config()["sections"]

            config["version"] = CURRENT_VERSION

        elif config_version > CURRENT_VERSION:
            logger.warning(f"Config version {config_version} is newer than supported {CURRENT_VERSION}. "
                          "Attempting best-effort read.")
            # Continue with current logic, trying to read what we can

        return config
