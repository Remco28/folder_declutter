"""
Drag-and-Drop Bridge Service
Handles drag-and-drop integration using tkinterdnd2 with file path normalization
"""

import logging
from typing import List, Callable, Optional

logger = logging.getLogger(__name__)

# Try to import tkinterdnd2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKINTERDND2_AVAILABLE = True
except ImportError:
    TKINTERDND2_AVAILABLE = False
    logger.warning("tkinterdnd2 not available - drag-and-drop features disabled")


class DragDropBridge:
    """
    Bridge for drag-and-drop operations using tkinterdnd2
    Handles file path normalization and widget registration
    """

    def __init__(self, root, pass_through_controller=None, logger=None):
        """
        Initialize drag-drop bridge

        Args:
            root: Tkinter root window
            pass_through_controller: PassThroughController for coordination
            logger: Logger instance (optional)
        """
        self.root = root
        self.pass_through_controller = pass_through_controller
        self.logger = logger or logging.getLogger(__name__)
        self.enabled = False

        # Track pass-through state during drag operations
        self._was_pass_through_enabled = False
        self._drag_in_progress = False

        if TKINTERDND2_AVAILABLE:
            # Root should already be a TkinterDnD.Tk() instance from main.py
            self.enabled = True
            self.logger.info("DragDropBridge initialized successfully")
        else:
            self.logger.warning("tkinterdnd2 not available - drag-drop disabled")

    def register_widget(self, widget, on_enter: Callable, on_leave: Callable, on_drop: Callable) -> None:
        """
        Register a widget as a drop target

        Args:
            widget: Tkinter widget to register
            on_enter: Callback for drag enter event
            on_leave: Callback for drag leave event
            on_drop: Callback for drop event
        """
        if not self.enabled:
            return

        try:
            # Register widget as drop target for files
            widget.drop_target_register(DND_FILES)

            # Bind drag-and-drop events
            widget.dnd_bind('<<DropEnter>>', on_enter)
            widget.dnd_bind('<<DropLeave>>', on_leave)
            widget.dnd_bind('<<Drop>>', on_drop)

            self.logger.debug(f"Registered drop target for widget: {widget}")

        except Exception as e:
            self.logger.error(f"Failed to register widget as drop target: {e}")

    @staticmethod
    def parse_drop_data(data: str) -> List[str]:
        """
        Parse drop data string into list of absolute paths
        Handles Windows-style brace-wrapped paths with spaces

        Args:
            data: Raw drop data string

        Returns:
            List of normalized absolute file paths

        Examples:
            '{C:\\A File.txt} {C:\\Dir With Spaces} C:\\PlainPath'
            -> ['C:\\A File.txt', 'C:\\Dir With Spaces', 'C:\\PlainPath']
        """
        if not data:
            return []

        items = []
        buf = ''
        in_braces = False

        for ch in data:
            if ch == '{':
                in_braces = True
                continue
            elif ch == '}':
                in_braces = False
                if buf.strip():
                    items.append(buf.strip())
                buf = ''
                continue
            elif ch == ' ' and not in_braces:
                if buf.strip():
                    items.append(buf.strip())
                buf = ''
                continue
            else:
                buf += ch

        # Add final item if exists
        if buf.strip():
            items.append(buf.strip())

        # Filter out empty items and return
        result = [item for item in items if item]
        logger.debug(f"Parsed drop data: {data} -> {result}")
        return result

    def _start_drag_sequence(self):
        """Start a drag sequence - disable pass-through and track original state"""
        if not self._drag_in_progress and self.pass_through_controller:
            self._was_pass_through_enabled = self.pass_through_controller.is_enabled()
            if self._was_pass_through_enabled:
                self.pass_through_controller.disable()
            self._drag_in_progress = True
            self.logger.debug(f"Drag sequence started, was_enabled: {self._was_pass_through_enabled}")

    def _end_drag_sequence(self):
        """End a drag sequence - restore original pass-through state"""
        if self._drag_in_progress and self.pass_through_controller:
            if self._was_pass_through_enabled:
                self.pass_through_controller.enable()
            self._drag_in_progress = False
            self.logger.debug(f"Drag sequence ended, restored: {self._was_pass_through_enabled}")

    def is_available(self) -> bool:
        """Check if drag-and-drop is available"""
        return self.enabled