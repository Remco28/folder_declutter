"""
File Operations - Threaded file move operations with conflict handling
"""

import os
import shutil
import logging
import uuid
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Optional, Any
from ..config import ConfigManager
from .error_handler import log_error


logger = logging.getLogger(__name__)


class FileOperations:
    """
    Handles file operations in background threads with UI callbacks
    """

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

                # Stop if operation was cancelled
                if result.get('cancelled'):
                    break

            finished_at = datetime.now()
            batch_result = {
                'items': items,
                'started_at': started_at,
                'finished_at': finished_at
            }

            self.logger.info(f"Move operation completed: {len(items)} items processed")
            self._call_main_thread(lambda: on_done(batch_result, actions))

        self.executor.submit(work)

    def _move_one(self, src: Path, dest: Path, backups_dir: Path, options: Dict) -> tuple[Dict, List[Dict]]:
        """
        Move a single file/folder with conflict handling

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

            self.logger.debug(f"Moved: {src} -> {dest}")

        except Exception as e:
            error_msg = log_error(e, str(src), self.logger)
            result['status'] = 'error'
            result['error'] = error_msg

        return result, actions

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
        appdata_dir = ConfigManager.get_appdata_dir()
        backups_dir = appdata_dir / "backups" / self.session_id

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

    def shutdown(self):
        """Clean shutdown of thread pool"""
        self.executor.shutdown(wait=True)