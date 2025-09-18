"""
Windows Integration Service
Handles Windows-specific functionality including pass-through behavior using pywin32
"""

import sys
import logging
from contextlib import contextmanager
from typing import Optional, NamedTuple

logger = logging.getLogger(__name__)

# Windows constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8

# Icon constants
WM_SETICON = 0x80
ICON_SMALL = 0
ICON_BIG = 1

# SHGetFileInfo constants
SHGFI_ICON = 0x100
SHGFI_LARGEICON = 0x0
SHGFI_SMALLICON = 0x1
SHGFI_USEFILEATTRIBUTES = 0x10
FILE_ATTRIBUTE_DIRECTORY = 0x10

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

    # ctypes imports for icon functionality (always available on Windows)
    try:
        import ctypes
        from ctypes import wintypes, byref, sizeof, windll
        CTYPES_AVAILABLE = True
    except ImportError:
        CTYPES_AVAILABLE = False
        logger.warning("ctypes not available - icon functionality disabled")
else:
    PYWIN32_AVAILABLE = False
    CTYPES_AVAILABLE = False


# ctypes structures for Windows API
if IS_WINDOWS and CTYPES_AVAILABLE:
    class SHFILEINFOW(ctypes.Structure):
        """Windows SHFILEINFOW structure for SHGetFileInfoW"""
        _fields_ = [
            ("hIcon", wintypes.HICON),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", wintypes.WCHAR * 260),
            ("szTypeName", wintypes.WCHAR * 80)
        ]

    class _IconHandles(NamedTuple):
        """Container for large and small icon handles"""
        large: wintypes.HICON
        small: wintypes.HICON


def _get_last_error() -> int:
    """Return the last Win32 error code if available."""
    if not IS_WINDOWS or not CTYPES_AVAILABLE:
        return 0
    try:
        return windll.kernel32.GetLastError()
    except Exception:
        return 0


def _load_standard_folder_icons() -> Optional['_IconHandles']:
    """
    Load standard Windows folder icons (large and small) using SHGetFileInfoW

    Returns:
        _IconHandles with large and small icon handles, or None if loading fails
    """
    if not IS_WINDOWS or not CTYPES_AVAILABLE:
        return None

    try:
        shell32 = windll.shell32
        flags = SHGFI_ICON | SHGFI_USEFILEATTRIBUTES

        # Load large icon
        info_large = SHFILEINFOW()
        result_large = shell32.SHGetFileInfoW(
            "C:\\",  # Use generic path for folder
            FILE_ATTRIBUTE_DIRECTORY,
            byref(info_large),
            sizeof(info_large),
            flags | SHGFI_LARGEICON
        )

        # Load small icon
        info_small = SHFILEINFOW()
        result_small = shell32.SHGetFileInfoW(
            "C:\\",  # Use generic path for folder
            FILE_ATTRIBUTE_DIRECTORY,
            byref(info_small),
            sizeof(info_small),
            flags | SHGFI_SMALLICON
        )

        if result_large and result_small and info_large.hIcon and info_small.hIcon:
            logger.debug(f"Loaded folder icons: large={info_large.hIcon}, small={info_small.hIcon}")
            return _IconHandles(info_large.hIcon, info_small.hIcon)
        else:
            error_code = _get_last_error()
            logger.warning(f"Failed to load folder icons: large_result={result_large}, small_result={result_small}, error={error_code}")

            # Clean up any partial results
            if info_large.hIcon:
                windll.user32.DestroyIcon(info_large.hIcon)
            if info_small.hIcon:
                windll.user32.DestroyIcon(info_small.hIcon)
            return None

    except Exception as e:
        logger.error(f"Exception loading folder icons: {e}")
        return None


def set_window_icon_to_folder(hwnd: int, logger_instance: Optional[logging.Logger] = None) -> None:
    """
    Set the window icon to the standard Windows folder icon

    Args:
        hwnd: Windows handle of the target window
        logger_instance: Optional logger instance (defaults to module logger)
    """
    if not IS_WINDOWS or not CTYPES_AVAILABLE:
        return

    if not hwnd:
        if logger_instance:
            logger_instance.warning("Cannot set folder icon: invalid HWND")
        return

    log = logger_instance or logger

    try:
        # Load folder icons
        icons = _load_standard_folder_icons()
        if not icons:
            log.warning("Failed to load folder icons")
            return

        user32 = windll.user32

        # Set large icon and get previous handle
        prev_big = user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icons.large)
        if prev_big == 0:
            error_code = _get_last_error()
            log.debug(f"SendMessageW for large icon returned 0, error={error_code}")

        # Set small icon and get previous handle
        prev_small = user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icons.small)
        if prev_small == 0:
            error_code = _get_last_error()
            log.debug(f"SendMessageW for small icon returned 0, error={error_code}")

        log.info(f"Set folder icon for HWND {hwnd}")

        # Clean up all handles (new icons we created and any previous icons)
        handles_to_destroy = [icons.large, icons.small]
        if prev_big:
            handles_to_destroy.append(prev_big)
        if prev_small:
            handles_to_destroy.append(prev_small)

        for handle in handles_to_destroy:
            if handle:
                try:
                    result = user32.DestroyIcon(handle)
                    if not result:
                        error_code = _get_last_error()
                        log.debug(f"DestroyIcon({handle}) failed, error={error_code}")
                except Exception as e:
                    log.debug(f"Exception destroying icon handle {handle}: {e}")

        log.debug(f"Cleaned up {len(handles_to_destroy)} icon handles")

    except Exception as e:
        log.error(f"Exception setting folder icon: {e}")


def get_hwnd(tk_root) -> Optional[int]:
    """
    Get Windows handle (HWND) for a Tkinter root window

    Args:
        tk_root: Tkinter root window

    Returns:
        HWND as integer, or None if not available
    """
    if not IS_WINDOWS:
        return None

    try:
        # Get the window ID from Tkinter
        winfo_id = tk_root.winfo_id()

        # Try pywin32 first if available
        if PYWIN32_AVAILABLE:
            # Convert to Windows HWND
            hwnd = win32gui.GetParent(winfo_id)
            if hwnd == 0:
                hwnd = winfo_id
            return hwnd

        # Fall back to ctypes if pywin32 is not available
        elif CTYPES_AVAILABLE:
            user32 = windll.user32
            # Try GetParent first
            hwnd = user32.GetParent(winfo_id)
            if hwnd == 0:
                # If no parent, use the window ID directly
                hwnd = winfo_id
            return hwnd

        else:
            logger.warning("Neither pywin32 nor ctypes available - cannot get HWND")
            return None

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