"""
File Operations - Threaded file move operations with conflict handling
"""

import os
import shutil
import logging
import uuid
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Optional, Any, Set
from ..config import ConfigManager
from .error_handler import log_error
from ..services import shell_notify


logger = logging.getLogger(__name__)

# Platform detection and optional Windows shell imports
import sys
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    try:
        import pythoncom
        from win32com.shell import shell, shellcon
        from pywintypes import com_error
        PYWIN32_AVAILABLE = True
    except Exception:
        PYWIN32_AVAILABLE = False
else:
    PYWIN32_AVAILABLE = False


class FileOperations:
    """
    Handles file operations in background threads with UI callbacks
    """

    _cleanup_lock = threading.Lock()
    _startup_cleanup_done = False
    _shutdown_cleanup_done = False

    def __init__(self, root, logger=None):
        """
        Initialize file operations

        Args:
            root: Tkinter root window for thread-safe callbacks
            logger: Logger instance (optional)
        """
        self.root = root
        self.logger = logger or logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="FileOps")
        self.session_id = str(uuid.uuid4())[:8]
        self._run_startup_cleanup()

    def move_many(self, request: Dict, on_done: Callable) -> None:
        """
        Move multiple files/folders to target directory in background thread

        Args:
            request: MoveRequest dict with sources, target_dir, options
            on_done: Callback(batch_result, undo_actions) called on main thread
        """
        def work():
            sources = request.get('sources', [])
            target_dir = Path(request.get('target_dir', ''))
            options = request.get('options', {})

            # Collect touched directories for batch notification
            touched_dirs = set()

            self.logger.info(f"Starting move operation: {len(sources)} items to {target_dir}")

            # Ensure target directory exists
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                error_msg = log_error(e, str(target_dir), self.logger)
                batch_result = {
                    'items': [],
                    'started_at': datetime.now(),
                    'finished_at': datetime.now(),
                    'error': f"Failed to create target directory: {error_msg}"
                }
                self._call_main_thread(lambda: on_done(batch_result, []))
                return

            # Ensure session backups directory exists
            backups_dir = self._ensure_session_backups_dir()

            # Process each source file/folder
            items = []
            actions = []
            started_at = datetime.now()

            for src_path in sources:
                src = Path(src_path)
                if not src.exists():
                    items.append({
                        'src': str(src),
                        'dest': '',
                        'status': 'error',
                        'error': 'Source does not exist'
                    })
                    continue

                dest = target_dir / src.name
                result, item_actions = self._move_one(src, dest, backups_dir, options)
                items.append(result)
                actions.extend(item_actions)

                # Collect touched directories for successful moves
                if result.get('status') in ('ok', 'skipped'):
                    touched_dirs.add(str(src.parent.resolve()))
                    touched_dirs.add(str(dest.parent.resolve()))

                # Stop if operation was cancelled
                if result.get('cancelled'):
                    break

            finished_at = datetime.now()
            batch_result = {
                'items': items,
                'started_at': started_at,
                'finished_at': finished_at
            }

            # Batch notify all touched directories at the end
            self._shell_notify_many(touched_dirs)

            self.logger.info(f"Move operation completed: {len(items)} items processed")
            self._call_main_thread(lambda: on_done(batch_result, actions))

        self.executor.submit(work)

    def _move_one_shutil(self, src: Path, dest: Path, backups_dir: Path, options: Dict) -> tuple[Dict, List[Dict]]:
        """
        Move a single file/folder with conflict handling using shutil

        Args:
            src: Source path
            dest: Destination path
            backups_dir: Directory for backups
            options: Move options including overwrite preference

        Returns:
            tuple: (result_dict, undo_actions_list)
        """
        result = {
            'src': str(src),
            'dest': str(dest),
            'status': 'ok',
            'conflict': False
        }
        actions = []

        try:
            # Handle existing destination
            if dest.exists():
                result['conflict'] = True
                overwrite_choice = options.get('overwrite')

                if overwrite_choice is None:
                    # Need to prompt user - marshal to main thread
                    choice = self._prompt_overwrite_main_thread(dest)
                    if choice is None:
                        result['status'] = 'cancelled'
                        result['cancelled'] = True
                        return result, actions
                    overwrite_choice = choice

                if overwrite_choice == 'skip':
                    result['status'] = 'skipped'
                    return result, actions
                elif overwrite_choice == 'replace':
                    # Create backup before replacing
                    backup_path = self._make_unique_backup(dest, backups_dir)
                    shutil.move(str(dest), str(backup_path))
                    actions.append({
                        'kind': 'replace',
                        'dest': str(dest),
                        'backup': str(backup_path)
                    })
                    self.logger.debug(f"Created backup: {dest} -> {backup_path}")

            # Perform the actual move
            shutil.move(str(src), str(dest))
            actions.append({
                'kind': 'move',
                'src': str(src),
                'dest': str(dest)
            })

            # Notify shell of directory changes after successful move
            self._shell_notify_updatedir(src.parent)
            self._shell_notify_updatedir(dest.parent)

            self.logger.debug(f"Moved: {src} -> {dest}")

        except Exception as e:
            error_msg = log_error(e, str(src), self.logger)
            result['status'] = 'error'
            result['error'] = error_msg

        return result, actions

    def _move_one_windows_shell(self, src: Path, dest: Path, backups_dir: Path, options: Dict) -> tuple[Dict, List[Dict]]:
        """
        Move a single item using Windows IFileOperation (per-item to preserve cancel semantics)
        """
        result = {
            'src': str(src),
            'dest': str(dest),
            'status': 'ok',
            'conflict': False
        }
        actions: List[Dict] = []

        try:
            # If destination exists, handle conflict via prompt
            if dest.exists():
                result['conflict'] = True
                overwrite_choice = options.get('overwrite')
                if not overwrite_choice:
                    choice = self._prompt_overwrite_main_thread(dest)
                    if choice is None:
                        result['status'] = 'cancelled'
                        result['cancelled'] = True
                        return result, actions
                    overwrite_choice = choice

                if overwrite_choice == 'skip':
                    result['status'] = 'skipped'
                    return result, actions
                elif overwrite_choice == 'replace':
                    backup_path = self._make_unique_backup(dest, backups_dir)
                    shutil.move(str(dest), str(backup_path))
                    actions.append({
                        'kind': 'replace',
                        'dest': str(dest),
                        'backup': str(backup_path)
                    })
                    self.logger.debug(f"Created backup: {dest} -> {backup_path}")

            # Initialize COM in this worker thread
            pythoncom.CoInitialize()
            try:
                file_op = pythoncom.CoCreateInstance(
                    shell.CLSID_FileOperation,
                    None,
                    pythoncom.CLSCTX_INPROC_SERVER,
                    shell.IID_IFileOperation
                )

                flags = (
                    shellcon.FOF_SILENT |
                    shellcon.FOF_NOCONFIRMATION |
                    shellcon.FOF_NOCONFIRMMKDIR
                )
                extra_flag = getattr(shellcon, 'FOFX_NOCOPYSECURITYATTRIBS', 0)
                if extra_flag:
                    flags |= extra_flag
                file_op.SetOperationFlags(flags)

                abs_src = str(src.resolve())
                abs_target_dir = str(dest.parent.resolve())
                src_item = shell.SHCreateItemFromParsingName(abs_src, None, shell.IID_IShellItem)
                target_dir_item = shell.SHCreateItemFromParsingName(abs_target_dir, None, shell.IID_IShellItem)

                file_op.MoveItem(src_item, target_dir_item, None, None)

                try:
                    file_op.PerformOperations()
                except com_error as e:
                    self.logger.error(f"IFileOperation.PerformOperations failed: {e}")
                    raise
            finally:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

            actions.append({
                'kind': 'move',
                'src': str(src),
                'dest': str(dest)
            })

            # Notify shell of directory changes after successful move
            self._shell_notify_updatedir(src.parent)
            self._shell_notify_updatedir(dest.parent)

            self.logger.debug(f"Shell moved: {src} -> {dest}")

        except Exception as e:
            error_msg = log_error(e, str(src), self.logger)
            result['status'] = 'error'
            result['error'] = error_msg

        return result, actions

    def _move_one(self, src: Path, dest: Path, backups_dir: Path, options: Dict) -> tuple[Dict, List[Dict]]:
        """
        Dispatch to Windows shell move if available, else shutil
        """
        if IS_WINDOWS and PYWIN32_AVAILABLE:
            try:
                return self._move_one_windows_shell(src, dest, backups_dir, options)
            except Exception as e:
                self.logger.warning(f"Shell move failed for {src} -> {dest}, falling back to shutil: {e}")
                return self._move_one_shutil(src, dest, backups_dir, options)
        else:
            return self._move_one_shutil(src, dest, backups_dir, options)

    def _prompt_overwrite_main_thread(self, dest_path: Path) -> Optional[str]:
        """
        Prompt user for overwrite decision on main thread

        Args:
            dest_path: Path that already exists

        Returns:
            str|None: 'replace', 'skip', or None for cancel
        """
        from ..ui.dialogs import prompt_overwrite
        import queue
        import threading

        # Create a queue to get result from main thread
        result_queue = queue.Queue()

        def prompt_on_main():
            try:
                choice = prompt_overwrite(str(dest_path), parent=self.root)
                result_queue.put(choice)
            except Exception as e:
                self.logger.error(f"Error in overwrite prompt: {e}")
                result_queue.put(None)

        # Schedule prompt on main thread
        self.root.after(0, prompt_on_main)

        # Wait for result (blocking the worker thread)
        try:
            return result_queue.get(timeout=300)  # 5 minute timeout
        except queue.Empty:
            self.logger.error("Overwrite prompt timed out")
            return None

    def _make_unique_backup(self, path: Path, backups_dir: Path) -> Path:
        """
        Create unique backup filename in backups directory

        Args:
            path: Original file/folder path
            backups_dir: Backup directory

        Returns:
            Path: Unique backup path
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}_{timestamp}"

        backup_path = backups_dir / backup_name
        counter = 1
        while backup_path.exists():
            backup_name = f"{path.name}_{timestamp}_{counter}"
            backup_path = backups_dir / backup_name
            counter += 1

        return backup_path

    def _ensure_session_backups_dir(self) -> Path:
        """
        Ensure session-specific backups directory exists

        Returns:
            Path: Session backups directory
        """
        backups_dir = ConfigManager.get_backups_root() / self.session_id

        try:
            backups_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Session backups directory: {backups_dir}")
            return backups_dir
        except Exception as e:
            self.logger.error(f"Failed to create backups directory: {e}")
            # Fallback to temp directory
            import tempfile
            fallback = Path(tempfile.gettempdir()) / "DesktopSorter" / "backups" / self.session_id
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def _call_main_thread(self, callback: Callable):
        """
        Schedule callback to run on main thread

        Args:
            callback: Function to call on main thread
        """
        self.root.after(0, callback)

    def _shell_notify_updatedir(self, path: Path) -> None:
        """
        Notify Windows Shell that a directory has been updated

        Args:
            path: Directory path to notify about
        """
        # Delegate to centralized shell notify utility (handles PIDL/PATHW and platform guards)
        try:
            shell_notify.notify_updatedir(path)
            self.logger.debug(f"Shell UPDATEDIR notified for: {str(path)}")
        except Exception as e:
            self.logger.debug(f"notify_updatedir failed for {path}: {e}")

    def _shell_notify_many(self, touched_dirs: Set[str]) -> None:
        """
        Batch notify multiple directories and optionally Desktop roots

        Args:
            touched_dirs: Set of absolute directory paths that were modified
        """
        # Delegate to centralized shell notify utility (handles Desktop roots, PIDL/PATHW)
        try:
            shell_notify.notify_many(touched_dirs)
        except Exception as e:
            self.logger.debug(f"notify_many failed: {e}")

    def _get_desktop_folders(self) -> List[Path]:
        """
        Get Windows Desktop folder paths (user + public)

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
            self.logger.debug(f"Could not get user desktop path: {e}")

        try:
            # Public Desktop (if available)
            public_desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY, 0, 0)
            desktop_paths.append(Path(public_desktop))
        except Exception as e:
            self.logger.debug(f"Could not get public desktop path: {e}")

        return desktop_paths

    def shutdown(self):
        """Clean shutdown of thread pool"""
        self.executor.shutdown(wait=True)
        self._run_shutdown_cleanup()

    def _run_startup_cleanup(self) -> None:
        """Prune empty backup sessions once per process on startup."""
        cls = self.__class__
        with cls._cleanup_lock:
            if cls._startup_cleanup_done:
                return
            cls._startup_cleanup_done = True
        self._prune_empty_backup_sessions(skip_ids={self.session_id})

    def _run_shutdown_cleanup(self) -> None:
        """Prune empty backup sessions once when shutdown completes."""
        cls = self.__class__
        with cls._cleanup_lock:
            if cls._shutdown_cleanup_done:
                return
            cls._shutdown_cleanup_done = True
        self._prune_empty_backup_sessions()

    def _prune_empty_backup_sessions(self, skip_ids: Optional[Set[str]] = None) -> None:
        """Remove empty backup session directories without touching stored archives."""
        backups_root = ConfigManager.get_backups_root()

        try:
            if not backups_root.exists():
                return
        except OSError as exc:
            self.logger.debug("Skipping backup cleanup; cannot access %s: %s", backups_root, exc)
            return

        try:
            session_dirs = list(backups_root.iterdir())
        except OSError as exc:
            self.logger.debug("Skipping backup cleanup; failed to enumerate %s: %s", backups_root, exc)
            return

        skip_names = skip_ids or set()

        for session_dir in session_dirs:
            if not session_dir.is_dir():
                continue
            if session_dir.name in skip_names:
                continue

            try:
                has_children = any(session_dir.iterdir())
            except OSError as exc:
                self.logger.debug("Skipping backup cleanup for %s: %s", session_dir, exc)
                continue

            if has_children:
                continue

            try:
                session_dir.rmdir()
                self.logger.debug("Removed empty backup session directory %s", session_dir)
            except OSError as exc:
                self.logger.debug("Failed to remove empty backup directory %s: %s", session_dir, exc)
