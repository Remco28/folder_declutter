"""Utilities for locating resource files across source and bundled builds."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Anchor to the project root when running from source
# services/ -> src/ -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resource_path(*relative_parts: str) -> Optional[Path]:
    """Return the first existing path for the requested resource.

    When running from source, resources live under the project root. When
    bundled via PyInstaller, resources are extracted beneath ``sys._MEIPASS``.
    ``relative_parts`` should describe the path relative to the project root
    (e.g., ``('resources', 'icon.png')``).
    """

    parts_path = Path(*relative_parts)

    roots = []
    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))
    roots.append(_PROJECT_ROOT)

    # Fallback: current working directory (useful during manual testing)
    try:
        roots.append(Path.cwd())
    except Exception:
        pass

    seen = set()
    for root in roots:
        try:
            root = root.resolve()
        except Exception:
            continue
        if root in seen:
            continue
        seen.add(root)

        candidate = root / parts_path
        if candidate.exists():
            return candidate

    return None


def resource_path_or_default(*relative_parts: str, default: Optional[Path] = None) -> Optional[Path]:
    """Helper that mirrors :func:`resource_path` but falls back to ``default``."""

    path = resource_path(*relative_parts)
    return path if path is not None else default
