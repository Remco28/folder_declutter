"""
Config package for Desktop Sorter
Handles configuration persistence and management
"""

from .config_manager import ConfigManager
from .defaults import CURRENT_VERSION, default_config

__all__ = ['ConfigManager', 'CURRENT_VERSION', 'default_config']