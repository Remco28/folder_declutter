"""
Default configuration for Desktop Sorter
"""

import copy

CURRENT_VERSION = 1


def default_config() -> dict:
    """
    Return a deep copy of the default configuration

    Returns:
        dict: Default configuration with 6 empty sections (ids 0..5)
    """
    return copy.deepcopy({
        "version": CURRENT_VERSION,
        "sections": [
            {"id": 0, "label": None, "kind": "folder", "path": None},
            {"id": 1, "label": None, "kind": "folder", "path": None},
            {"id": 2, "label": None, "kind": "folder", "path": None},
            {"id": 3, "label": None, "kind": "folder", "path": None},
            {"id": 4, "label": None, "kind": "folder", "path": None},
            {"id": 5, "label": None, "kind": "folder", "path": None},
        ]
    })