"""
Shell notification utilities for Windows Explorer refresh.

Provides centralized Windows shell notification functionality to ensure
Explorer/Desktop views update immediately after file operations.

Uses PIDL (IDLIST) notifications by default to avoid Unicode conversion issues,
with optional PATHW fallback via DS_SHELL_NOTIFY_MODE environment variable.
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Set, Optional

logger = logging.getLogger(__name__)

# Platform detection and optional Windows shell imports
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
        PYWIN32_AVAILABLE = True
    except Exception:
        PYWIN32_AVAILABLE = False
else:
    PYWIN32_AVAILABLE = False


def notify_batch_delete_and_parents(paths: List[Path]) -> None:
    """
    Notify Windows Shell about batch delete operations and their parent directories.

    This is the main entry point for recycle bin notifications.

    Args:
        paths: List of deleted file/folder paths
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE:
        logger.info("Shell notifications skipped - not Windows or pywin32 unavailable")
        return

    if not paths:
        logger.debug("No paths provided for shell notifications")
        return

    # Get notification mode from environment variable
    mode = os.getenv('DS_SHELL_NOTIFY_MODE', 'pidl').lower()
    logger.info(f"Shell notification mode: {mode}")
    logger.info(f"Notifying about {len(paths)} deleted items and their parents")

    try:
        # Notify delete for each item
        for path in paths:
            if mode == 'pathw':
                _notify_delete_pathw(path)
            else:
                _notify_delete_pidl(path)

        # Compute parent directories and notify updatedir
        parents = {str(p.parent) for p in paths}
        logger.info(f"Notifying UPDATEDIR for {len(parents)} parent directories: {parents}")

        for parent_path in parents:
            parent = Path(parent_path)
            if mode == 'pathw':
                _notify_updatedir_pathw(parent)
            else:
                _notify_updatedir_pidl(parent)

        # Check Desktop roots and notify if any touched path is under them
        desktop_roots = get_desktop_folders()
        logger.info(f"Checking {len(desktop_roots)} desktop roots for notifications")
        for desktop_path in desktop_roots:
            desktop_str = str(desktop_path)
            if any(parent_path.startswith(desktop_str) for parent_path in parents):
                logger.info(f"Desktop root touched, notifying: {desktop_str}")
                if mode == 'pathw':
                    _notify_updatedir_pathw(desktop_path)
                else:
                    _notify_updatedir_pidl(desktop_path)
            else:
                logger.debug(f"No touched paths under desktop root: {desktop_str}")

    except Exception as e:
        logger.error(f"Batch shell notification failed: {e}")


def _pidl_from_path(abs_path: str) -> Optional[object]:
    """
    Convert absolute path to PIDL using SHParseDisplayName.

    Args:
        abs_path: Absolute path string

    Returns:
        PIDL object or None if conversion fails
    """
    try:
        # Note: Third parameter is an attribute mask (sfgaoIn). Pass 0, not None.
        # Some pywin32 builds error on None here.
        pidl, _attrs = shell.SHParseDisplayName(abs_path, None, 0)
        return pidl
    except Exception as e:
        logger.debug(f"Failed to create PIDL from path {abs_path}: {e}")
        return None


def _notify_delete_pidl(path: Path) -> None:
    """
    Notify shell about item deletion using PIDL.

    Args:
        path: Path that was deleted
    """
    try:
        abs_path = str(path.resolve())
        pidl = _pidl_from_path(abs_path)
        if pidl is None:
            # Deleted item PIDLs may not be creatable post-delete. Fallback to PATHW.
            logger.warning(f"Could not create PIDL for delete notification: {abs_path}")
            _notify_delete_pathw(path)
            return

        shell.SHChangeNotify(
            shellcon.SHCNE_DELETE,
            shellcon.SHCNF_IDLIST,
            pidl,
            None
        )
        logger.info(f"Shell notified DELETE (PIDL): {abs_path}")
    except Exception as e:
        logger.warning(f"PIDL delete notification failed for {path}: {e}")
        # Best-effort fallback to PATHW
        try:
            _notify_delete_pathw(path)
        except Exception:
            pass


def _notify_updatedir_pidl(path: Path) -> None:
    """
    Notify shell about directory update using PIDL.

    Args:
        path: Directory path that was updated
    """
    try:
        abs_path = str(path.resolve())
        pidl = _pidl_from_path(abs_path)
        if pidl is None:
            # Fallback to PATHW if PIDL creation fails (e.g., parsing quirks)
            logger.warning(f"Could not create PIDL for updatedir notification: {abs_path}")
            _notify_updatedir_pathw(path)
            return

        shell.SHChangeNotify(
            shellcon.SHCNE_UPDATEDIR,
            shellcon.SHCNF_IDLIST,
            pidl,
            None
        )
        logger.info(f"Shell notified UPDATEDIR (PIDL): {abs_path}")
    except Exception as e:
        logger.warning(f"PIDL updatedir notification failed for {path}: {e}")
        # Best-effort fallback to PATHW
        try:
            _notify_updatedir_pathw(path)
        except Exception:
            pass


def _notify_delete_pathw(path: Path) -> None:
    """
    Notify shell about item deletion using PATHW (fallback mode).

    Args:
        path: Path that was deleted
    """
    try:
        abs_path = str(path.resolve())
        shell.SHChangeNotify(
            shellcon.SHCNE_DELETE,
            shellcon.SHCNF_PATHW,
            abs_path,
            None
        )
        logger.info(f"Shell notified DELETE (PATHW): {abs_path}")
    except Exception as e:
        logger.warning(f"PATHW delete notification failed for {path}: {e}")


def _notify_updatedir_pathw(path: Path) -> None:
    """
    Notify shell about directory update using PATHW (fallback mode).

    Args:
        path: Directory path that was updated
    """
    try:
        abs_path = str(path.resolve())
        shell.SHChangeNotify(
            shellcon.SHCNE_UPDATEDIR,
            shellcon.SHCNF_PATHW,
            abs_path,
            None
        )
        logger.info(f"Shell notified UPDATEDIR (PATHW): {abs_path}")
    except Exception as e:
        logger.warning(f"PATHW updatedir notification failed for {path}: {e}")


def get_desktop_folders() -> List[Path]:
    """
    Get Windows Desktop folder paths (user + public).

    Returns:
        List of Desktop folder paths
    """
    desktop_paths = []
    if not IS_WINDOWS or not PYWIN32_AVAILABLE:
        return desktop_paths

    try:
        # User Desktop
        user_desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, 0, 0)
        desktop_paths.append(Path(user_desktop))
    except Exception as e:
        logger.debug(f"Could not get user desktop path: {e}")

    try:
        # Public Desktop (if available)
        public_desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY, 0, 0)
        desktop_paths.append(Path(public_desktop))
    except Exception as e:
        logger.debug(f"Could not get public desktop path: {e}")

    return desktop_paths


# Legacy compatibility functions for file operations
def notify_updatedir(path: Path) -> None:
    """
    Legacy function for single directory update notification.

    Args:
        path: Directory path to notify about
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE:
        return

    mode = os.getenv('DS_SHELL_NOTIFY_MODE', 'pidl').lower()
    if mode == 'pathw':
        _notify_updatedir_pathw(path)
    else:
        _notify_updatedir_pidl(path)


def notify_many(touched_dirs: Set[str]) -> None:
    """
    Legacy function for batch directory notifications.

    Args:
        touched_dirs: Set of absolute directory paths that were modified
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE:
        logger.info("Shell notifications skipped - not Windows or pywin32 unavailable")
        return

    logger.info(f"Shell notify_many called with {len(touched_dirs)} directories: {touched_dirs}")

    mode = os.getenv('DS_SHELL_NOTIFY_MODE', 'pidl').lower()

    try:
        # Notify all touched directories
        for dir_path in touched_dirs:
            path = Path(dir_path)
            if mode == 'pathw':
                _notify_updatedir_pathw(path)
            else:
                _notify_updatedir_pidl(path)

        # Belt-and-suspenders for Desktop folders
        desktop_roots = get_desktop_folders()
        logger.info(f"Checking {len(desktop_roots)} desktop roots for notifications")
        for desktop_path in desktop_roots:
            # Check if any touched path is under this Desktop
            desktop_str = str(desktop_path)
            if any(touched_dir.startswith(desktop_str) for touched_dir in touched_dirs):
                logger.info(f"Desktop root notified: {desktop_str}")
                if mode == 'pathw':
                    _notify_updatedir_pathw(desktop_path)
                else:
                    _notify_updatedir_pidl(desktop_path)
            else:
                logger.debug(f"No touched dirs under desktop root: {desktop_str}")

    except Exception as e:
        logger.error(f"Shell notification batch failed: {e}")
