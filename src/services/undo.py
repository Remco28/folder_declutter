"""
Undo Service - Session-only multi-level undo for file operations
"""

import logging
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable
from ..file_handler.error_handler import log_error


logger = logging.getLogger(__name__)


class UndoService:
    """
    Manages undo stack for file operations with LIFO behavior
    """

    def __init__(self, root, logger=None):
        """
        Initialize undo service

        Args:
            root: Tkinter root window for thread-safe callbacks
            logger: Logger instance (optional)
        """
        self.root = root
        self.logger = logger or logging.getLogger(__name__)
        self.undo_stack = []  # List of action batches (LIFO)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Undo")

    def can_undo(self) -> bool:
        """
        Check if undo is available

        Returns:
            bool: True if there are actions to undo
        """
        return len(self.undo_stack) > 0

    def push_batch(self, actions: List[Dict]) -> None:
        """
        Push a batch of actions onto the undo stack

        Args:
            actions: List of action dictionaries from file operations
        """
        if actions:
            self.undo_stack.append(actions)
            self.logger.info(f"Pushed {len(actions)} actions to undo stack (total batches: {len(self.undo_stack)})")

    def undo_last(self, on_done: Callable) -> None:
        """
        Undo the most recent batch of actions in background thread

        Args:
            on_done: Callback(success_count, failure_count) called on main thread
        """
        if not self.can_undo():
            self._call_main_thread(lambda: on_done(0, 0))
            return

        def work():
            actions = self.undo_stack.pop()
            self.logger.info(f"Undoing batch with {len(actions)} actions")

            success_count = 0
            failure_count = 0

            # Process actions in reverse order
            for action in reversed(actions):
                try:
                    if self._undo_action(action):
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    log_error(e, action.get('dest', ''), self.logger)
                    failure_count += 1

            self.logger.info(f"Undo completed: {success_count} successful, {failure_count} failed")
            self._call_main_thread(lambda: on_done(success_count, failure_count))

        self.executor.submit(work)

    def _undo_action(self, action: Dict) -> bool:
        """
        Undo a single action

        Args:
            action: Action dictionary to undo

        Returns:
            bool: True if successful, False otherwise
        """
        action_kind = action.get('kind')

        try:
            if action_kind == 'move':
                return self._undo_move_action(action)
            elif action_kind == 'replace':
                return self._undo_replace_action(action)
            else:
                self.logger.warning(f"Unknown action kind: {action_kind}")
                return False

        except Exception as e:
            log_error(e, action.get('dest', ''), self.logger)
            return False

    def _undo_move_action(self, action: Dict) -> bool:
        """
        Undo a move action by moving back to original location

        Args:
            action: Move action dict with 'src' and 'dest'

        Returns:
            bool: True if successful
        """
        src = Path(action['src'])
        dest = Path(action['dest'])

        # Check if destination still exists
        if not dest.exists():
            self.logger.warning(f"Cannot undo move: destination {dest} no longer exists")
            return False

        # Check if source directory exists, create if needed
        src_parent = src.parent
        if not src_parent.exists():
            try:
                src_parent.mkdir(parents=True, exist_ok=True)
                self.logger.debug(f"Created parent directory for undo: {src_parent}")
            except Exception as e:
                log_error(e, str(src_parent), self.logger)
                return False

        # Check if source path is now occupied
        if src.exists():
            self.logger.warning(f"Cannot undo move: source {src} is now occupied")
            return False

        # Move back to original location
        shutil.move(str(dest), str(src))
        self.logger.debug(f"Undid move: {dest} -> {src}")
        return True

    def _undo_replace_action(self, action: Dict) -> bool:
        """
        Undo a replace action by restoring from backup

        Args:
            action: Replace action dict with 'dest' and 'backup'

        Returns:
            bool: True if successful
        """
        dest = Path(action['dest'])
        backup = Path(action['backup'])

        # Check if backup still exists
        if not backup.exists():
            self.logger.warning(f"Cannot undo replace: backup {backup} no longer exists")
            return False

        # Restore original file from backup
        # If dest exists, it will be overwritten
        shutil.move(str(backup), str(dest))
        self.logger.debug(f"Undid replace: restored {backup} -> {dest}")

        # Clean up backup directory if empty
        try:
            backup.parent.rmdir()
            self.logger.debug(f"Cleaned up empty backup directory: {backup.parent}")
        except OSError:
            # Directory not empty or other error, ignore
            pass

        return True

    def _call_main_thread(self, callback: Callable):
        """
        Schedule callback to run on main thread

        Args:
            callback: Function to call on main thread
        """
        self.root.after(0, callback)

    def clear_stack(self):
        """Clear the undo stack"""
        self.undo_stack.clear()
        self.logger.info("Undo stack cleared")

    def get_stack_depth(self) -> int:
        """Get current undo stack depth"""
        return len(self.undo_stack)

    def shutdown(self):
        """Clean shutdown of thread pool"""
        self.executor.shutdown(wait=True)