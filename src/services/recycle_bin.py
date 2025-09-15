"""
Recycle Bin Service - Windows recycle bin operations via IFileOperation/SHFileOperation
"""

import sys
import os
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Optional
from ..file_handler.error_handler import log_error
from . import shell_notify

logger = logging.getLogger(__name__)

# Platform detection and imports
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32gui
        import win32con
        import pythoncom
        from win32com.shell import shell, shellcon
        from pywintypes import com_error
        PYWIN32_AVAILABLE = True
    except ImportError:
        PYWIN32_AVAILABLE = False
        logger.warning("pywin32 not available - Recycle Bin operations disabled")
else:
    PYWIN32_AVAILABLE = False


class RecycleBinService:
    """
    Handles Windows Recycle Bin operations using shell APIs
    """

    def __init__(self, root, logger=None):
        """
        Initialize recycle bin service

        Args:
            root: Tkinter root window for thread-safe callbacks
            logger: Logger instance (optional)
        """
        self.root = root
        self.logger = logger or logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="RecycleBin")

        if not IS_WINDOWS:
            self.logger.warning("RecycleBinService: Windows integration disabled on non-Windows platform")
        elif not PYWIN32_AVAILABLE:
            self.logger.warning("RecycleBinService: pywin32 not available - recycle bin operations disabled")

    def is_available(self) -> bool:
        """
        Check if recycle bin operations are available

        Returns:
            bool: True if operations are available (Windows with pywin32)
        """
        return IS_WINDOWS and PYWIN32_AVAILABLE

    def delete_many(self, paths: List[str], on_done: Callable) -> None:
        """
        Delete files/folders to recycle bin in background thread

        Args:
            paths: List of file/folder paths to delete
            on_done: Callback(results) called on main thread with list of result dicts
        """
        if not self.is_available():
            # Return error results for all paths
            results = [
                {"path": path, "status": "error", "error": "Recycle bin operations not available"}
                for path in paths
            ]
            self._call_main_thread(lambda: on_done(results))
            return

        def work():
            self.logger.info(f"Starting recycle bin operation: {len(paths)} items")

            # Try IFileOperation first (preferred for Vista+)
            try:
                results = self._delete_with_ifileoperation(paths)
            except Exception as e:
                self.logger.warning(f"IFileOperation setup failed, falling back to SHFileOperation: {e}")
                try:
                    results = self._delete_with_shfileoperation(paths)
                except Exception as e2:
                    self.logger.error(f"SHFileOperation also failed: {e2}")
                    results = [
                        {"path": path, "status": "error", "error": str(e2)}
                        for path in paths
                    ]

            success_count = sum(1 for r in results if r["status"] == "ok")
            error_count = len(results) - success_count
            self.logger.info(f"Recycle bin operation completed: {success_count} successful, {error_count} failed")

            # Schedule shell notifications on main thread before calling on_done
            def notify_and_callback():
                self._notify_shell_after_delete(results)
                on_done(results)

            self._call_main_thread(notify_and_callback)

        self.executor.submit(work)

    def _delete_with_ifileoperation(self, paths: List[str]) -> List[Dict]:
        """
        Delete files using IFileOperation (Vista+)

        Args:
            paths: List of paths to delete

        Returns:
            List of result dictionaries

        Raises:
            Exception: If setup fails (COM init, object creation, or flag setting)
                      to allow fallback to SHFileOperation
        """
        results = []

        try:
            # Setup phase - any failure here should trigger fallback
            # Initialize COM in this thread
            pythoncom.CoInitialize()

            # Create IFileOperation object
            file_op = pythoncom.CoCreateInstance(
                shell.CLSID_FileOperation,
                None,
                pythoncom.CLSCTX_ALL,
                shell.IID_IFileOperation
            )

            # Set operation flags - allow undo (recycle bin), no confirmations, silent
            flags = (
                shellcon.FOF_ALLOWUNDO |  # Send to recycle bin
                shellcon.FOF_NOCONFIRMMKDIR |  # Don't confirm directory creation
                shellcon.FOF_SILENT |  # Don't show progress dialog
                shellcon.FOF_NOCONFIRMATION  # Don't confirm each delete
            )

            # Add optional flag if available (compatibility for older pywin32/SDKs)
            extra_flag = getattr(shellcon, 'FOFX_NOCOPYSECURITYATTRIBS', 0)
            if extra_flag:
                flags |= extra_flag
            else:
                logger.debug('IFileOperation: FOFX_NOCOPYSECURITYATTRIBS not available; proceeding without it')
            file_op.SetOperationFlags(flags)

        except Exception as e:
            # Setup failed - re-raise to trigger SHFileOperation fallback
            try:
                pythoncom.CoUninitialize()
            except:
                pass  # Ignore cleanup errors
            raise e

        # Per-item operations phase - individual failures are handled in results
        try:
            # Add each item to delete operation
            for path in paths:
                try:
                    # Convert path to absolute Windows path
                    abs_path = str(Path(path).resolve())

                    # Create shell item for the path
                    shell_item = shell.SHCreateItemFromParsingName(abs_path, None, shell.IID_IShellItem)

                    # Add to delete operation
                    file_op.DeleteItem(shell_item, None)

                    # Assume success (we'll catch failures during PerformOperations)
                    results.append({"path": path, "status": "ok"})

                except Exception as e:
                    error_msg = log_error(e, path, self.logger)
                    results.append({"path": path, "status": "error", "error": error_msg})

            # Execute all operations
            if results:  # Only if we have operations to perform
                try:
                    file_op.PerformOperations()
                except com_error as e:
                    # If perform operations fails, mark all pending operations as failed
                    self.logger.error(f"PerformOperations failed: {e}")
                    for result in results:
                        if result["status"] == "ok":
                            result["status"] = "error"
                            result["error"] = f"Batch operation failed: {e}"

        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass  # Ignore cleanup errors

        return results

    def _delete_with_shfileoperation(self, paths: List[str]) -> List[Dict]:
        """
        Delete files using SHFileOperation (fallback for older systems)

        Args:
            paths: List of paths to delete

        Returns:
            List of result dictionaries
        """
        try:
            # Convert paths to absolute paths and create null-terminated string
            abs_paths = []
            for path in paths:
                abs_path = str(Path(path).resolve())
                abs_paths.append(abs_path)

            # Create double-null-terminated string for SHFileOperation
            path_string = '\0'.join(abs_paths) + '\0\0'

            # Prepare operation structure
            shell_op = (
                0,  # hwnd (no parent window)
                shellcon.FO_DELETE,  # operation type
                path_string,  # source files
                None,  # destination (not used for delete)
                shellcon.FOF_ALLOWUNDO | shellcon.FOF_SILENT | shellcon.FOF_NOCONFIRMATION,  # flags
                None,  # progress title
                None   # progress routine
            )

            # Execute operation
            result_code, aborted = shell.SHFileOperation(shell_op)

            # Create results based on operation success
            if result_code == 0 and not aborted:
                results = [{"path": path, "status": "ok"} for path in paths]
            else:
                error_msg = f"SHFileOperation failed with code {result_code}"
                if aborted:
                    error_msg += " (aborted by user)"
                results = [
                    {"path": path, "status": "error", "error": error_msg}
                    for path in paths
                ]

        except Exception as e:
            error_msg = log_error(e, None, self.logger)
            results = [
                {"path": path, "status": "error", "error": error_msg}
                for path in paths
            ]

        return results

    def _notify_shell_after_delete(self, results: List[Dict]) -> None:
        """
        Notify Windows Shell about deleted items and their parent directories

        Args:
            results: List of delete operation results
        """
        # Extract successfully deleted paths
        deleted_paths = [
            Path(r['path']).resolve()
            for r in results
            if r.get('status') == 'ok'
        ]

        if deleted_paths:
            self.logger.info(f"Notifying shell about {len(deleted_paths)} deleted items and their parents")
            shell_notify.notify_batch_delete_and_parents(deleted_paths)
        else:
            self.logger.info("No successful deletes found, skipping shell notifications")

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
        self.logger.debug("RecycleBinService shutdown complete")