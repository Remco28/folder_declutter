"""
Windows Integration Service
Handles Windows-specific functionality including pass-through behavior using pywin32
"""

import sys
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Windows constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8

# Platform detection and imports
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32gui
        import win32con
        PYWIN32_AVAILABLE = True
    except ImportError:
        PYWIN32_AVAILABLE = False
        logger.warning("pywin32 not available - Windows integration disabled")
else:
    PYWIN32_AVAILABLE = False


def get_hwnd(tk_root) -> Optional[int]:
    """
    Get Windows handle (HWND) for a Tkinter root window
    
    Args:
        tk_root: Tkinter root window
        
    Returns:
        HWND as integer, or None if not available
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE:
        return None
    
    try:
        # Get the window ID from Tkinter
        winfo_id = tk_root.winfo_id()
        # Convert to Windows HWND
        hwnd = win32gui.GetParent(winfo_id)
        if hwnd == 0:
            hwnd = winfo_id
        return hwnd
    except Exception as e:
        logger.error(f"Failed to get HWND: {e}")
        return None


def enable_pass_through(hwnd: int) -> None:
    """
    Enable window pass-through by setting WS_EX_TRANSPARENT only.
    We avoid WS_EX_LAYERED to prevent Tk rendering issues unless paired with SetLayeredWindowAttributes.

    Args:
        hwnd: Windows handle
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE or not hwnd:
        return
    
    try:
        # Get current extended styles
        ex_style = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
        
        # Add only transparent flag (avoid WS_EX_LAYERED to prevent blank window)
        new_style = ex_style | WS_EX_TRANSPARENT
        
        # Apply new styles
        win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, new_style)
        
        logger.debug("Pass-through enabled")
        
    except Exception as e:
        logger.error(f"Failed to enable pass-through: {e}")


def disable_pass_through(hwnd: int) -> None:
    """
    Disable window pass-through by clearing both WS_EX_TRANSPARENT and WS_EX_LAYERED (defensive cleanup)

    Args:
        hwnd: Windows handle
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE or not hwnd:
        return
    
    try:
        # Get current extended styles
        ex_style = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
        
        # Remove both transparent and layered flags (defensive cleanup)
        new_style = ex_style & ~(WS_EX_TRANSPARENT | WS_EX_LAYERED)
        
        # Apply new styles
        win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, new_style)
        
        logger.debug("Pass-through disabled")
        
    except Exception as e:
        logger.error(f"Failed to disable pass-through: {e}")


def set_always_on_top(hwnd: int, on: bool) -> None:
    """
    Set or remove always-on-top behavior
    
    Args:
        hwnd: Windows handle
        on: True to enable always-on-top, False to disable
    """
    if not IS_WINDOWS or not PYWIN32_AVAILABLE or not hwnd:
        return
    
    try:
        if on:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )
        else:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
            )
        
        logger.debug(f"Always-on-top {'enabled' if on else 'disabled'}")
        
    except Exception as e:
        logger.error(f"Failed to set always-on-top: {e}")


class PassThroughController:
    """
    Controls Windows pass-through behavior with safe state transitions
    """
    
    def __init__(self):
        self.hwnd: Optional[int] = None
        self.enabled = False
        self._initialized = False
        
        if not IS_WINDOWS:
            logger.warning("PassThroughController: Windows integration disabled on non-Windows platform")
        elif not PYWIN32_AVAILABLE:
            logger.warning("PassThroughController: pywin32 not available - pass-through disabled")
    
    def attach(self, tk_root) -> None:
        """
        Attach controller to a Tkinter root window
        
        Args:
            tk_root: Tkinter root window
        """
        if not IS_WINDOWS or not PYWIN32_AVAILABLE:
            self._initialized = True
            return
        
        self.hwnd = get_hwnd(tk_root)
        if self.hwnd:
            logger.info(f"PassThroughController attached to HWND {self.hwnd}")
            self._initialized = True
        else:
            logger.error("Failed to attach PassThroughController - could not get HWND")
    
    def enable(self) -> None:
        """Enable pass-through (idempotent)"""
        if not self._initialized or self.enabled:
            return
        
        if self.hwnd:
            enable_pass_through(self.hwnd)
            self.enabled = True
            logger.info("Pass-through enabled")
    
    def disable(self) -> None:
        """Disable pass-through (idempotent)"""
        if not self._initialized or not self.enabled:
            return
        
        if self.hwnd:
            disable_pass_through(self.hwnd)
            self.enabled = False
            logger.info("Pass-through disabled")
    
    def toggle(self) -> None:
        """Toggle pass-through state (for debug mode)"""
        if self.enabled:
            self.disable()
        else:
            self.enable()
    
    @contextmanager
    def temporarily_disable_while(self, func):
        """
        Context manager to temporarily disable pass-through during function execution
        
        Args:
            func: Function to execute while pass-through is disabled
            
        Yields:
            Result of func()
        """
        was_enabled = self.enabled
        
        if was_enabled:
            self.disable()
        
        try:
            yield func()
        finally:
            if was_enabled:
                self.enable()
    
    def is_enabled(self) -> bool:
        """Check if pass-through is currently enabled"""
        return self.enabled
    
    def is_available(self) -> bool:
        """Check if pass-through functionality is available"""
        return IS_WINDOWS and PYWIN32_AVAILABLE and self._initialized