"""
Windows Layered Overlay - Native Windows overlay with per-pixel alpha
Uses WS_EX_LAYERED and UpdateLayeredWindow for perfect transparency
"""

import logging
import time
import platform
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

# Only import on Windows
if platform.system() == 'Windows':
    try:
        import ctypes
        from ctypes import wintypes
        import win32gui
        import win32con
        import win32api
        from PIL import Image

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        class BLENDFUNCTION(ctypes.Structure):
            """ctypes representation of the Win32 BLENDFUNCTION struct."""

            _fields_ = [
                ('BlendOp', ctypes.c_ubyte),
                ('BlendFlags', ctypes.c_ubyte),
                ('SourceConstantAlpha', ctypes.c_ubyte),
                ('AlphaFormat', ctypes.c_ubyte),
            ]

        WINDOWS_AVAILABLE = True
    except ImportError:
        WINDOWS_AVAILABLE = False
else:
    WINDOWS_AVAILABLE = False


class LayeredOverlay:
    """Windows layered overlay window with per-pixel alpha"""

    def __init__(self, on_restore: Callable[[], None], logger=None):
        """
        Initialize layered overlay

        Args:
            on_restore: Callback when overlay is clicked to restore
            logger: Optional logger instance
        """
        if not WINDOWS_AVAILABLE:
            raise RuntimeError("LayeredOverlay requires Windows with pywin32 and Pillow")

        self.on_restore = on_restore
        self.logger = logger or logging.getLogger(__name__)

        # Window state
        self.hwnd = None
        self.width = 0
        self.height = 0
        self.is_visible = False

        # Optional move tracking for future diagnostics
        self.in_move_loop = False

        # GDI resources
        self.hdc_screen = None
        self.hdc_mem = None
        self.hbitmap = None
        self.old_bitmap = None

        self.logger.debug("LayeredOverlay initialized")

    def create(self, image: 'Image.Image', x: int, y: int) -> None:
        """
        Create and show the layered window with given image at position

        Args:
            image: PIL Image with RGBA data
            x, y: Position to place window
        """
        if self.hwnd:
            self.destroy()

        try:
            self.width, self.height = image.size

            # Register window class with double-click support
            wc = win32gui.WNDCLASS()
            wc.hInstance = win32gui.GetModuleHandle(None)
            wc.lpszClassName = "LayeredOverlayClass"
            wc.lpfnWndProc = self._window_proc
            # Use a stock NULL_BRUSH so the window stays transparent without pywin32
            # complaining about a missing HBRUSH handle (pywin32 >= 306 rejects None).
            wc.hbrBackground = win32gui.GetStockObject(win32con.NULL_BRUSH)
            wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
            wc.style = win32con.CS_DBLCLKS  # Enable double-click messages

            try:
                win32gui.RegisterClass(wc)
            except Exception:
                # Class might already be registered
                pass

            # Create layered window
            self.hwnd = win32gui.CreateWindowEx(
                win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_TOPMOST,
                "LayeredOverlayClass",
                "LayeredOverlay",
                win32con.WS_POPUP,
                x, y, self.width, self.height,
                0, 0, win32gui.GetModuleHandle(None), None
            )

            if not self.hwnd:
                raise RuntimeError("Failed to create layered window")

            # Prepare ARGB bitmap
            self._create_argb_bitmap(image)

            # Update layered window with per-pixel alpha
            self._update_layered_window(x, y)

            # Show window
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            self.is_visible = True

            self.logger.info(f"LayeredOverlay created at ({x}, {y}) size {self.width}x{self.height}")

        except Exception as e:
            self.logger.error(f"Error creating layered overlay: {e}")
            self.destroy()
            raise

    def _create_argb_bitmap(self, image: 'Image.Image') -> None:
        """Create ARGB bitmap from PIL image"""
        try:
            # Convert to RGBA if needed
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            # Get screen DC
            self.hdc_screen = win32gui.GetDC(0)

            # Create memory DC compatible with screen
            self.hdc_mem = win32gui.CreateCompatibleDC(self.hdc_screen)

            # For layered windows, we need to use a different approach
            # Create a 32-bit bitmap and manually set the pixel data

            # Create BITMAPINFO structure for 32-bit ARGB
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ('biSize', wintypes.DWORD),
                    ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD),
                    ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD),
                    ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG),
                    ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD),
                ]

            class BITMAPINFO(ctypes.Structure):
                _fields_ = [
                    ('bmiHeader', BITMAPINFOHEADER),
                    ('bmiColors', wintypes.DWORD * 3),
                ]

            # Fill bitmap info
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = self.width
            bmi.bmiHeader.biHeight = -self.height  # Top-down bitmap
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0  # BI_RGB

            # Get image data as premultiplied BGRA for Windows layered windows
            r, g, b, a = image.split()
            try:
                from PIL import ImageChops
                rp = ImageChops.multiply(r, a)  # r * a / 255
                gp = ImageChops.multiply(g, a)
                bp = ImageChops.multiply(b, a)
            except Exception:
                # Fallback: no premultiply (may cause slight edge halos)
                rp, gp, bp = r, g, b

            # Reorder to BGRA by placing B in R slot, etc., then get raw bytes
            bgra_image = Image.merge('RGBA', (bp, gp, rp, a))
            bgra_data = bgra_image.tobytes()

            # Create DIB section using ctypes
            gdi32 = ctypes.windll.gdi32
            bits_ptr = ctypes.POINTER(ctypes.c_ubyte)()

            self.hbitmap = gdi32.CreateDIBSection(
                self.hdc_screen,
                ctypes.byref(bmi),
                0,  # DIB_RGB_COLORS
                ctypes.byref(bits_ptr),
                None,
                0
            )

            if not self.hbitmap:
                raise RuntimeError("Failed to create DIB section")

            # Copy image data to bitmap
            if bits_ptr:
                memmove = ctypes.cdll.msvcrt.memmove
                memmove(bits_ptr, bgra_data, len(bgra_data))

            # Select bitmap into memory DC
            self.old_bitmap = win32gui.SelectObject(self.hdc_mem, self.hbitmap)

            self.logger.debug(f"ARGB bitmap created: {self.width}x{self.height}")

        except Exception as e:
            self.logger.error(f"Error creating ARGB bitmap: {e}")
            self._cleanup_gdi_resources()
            raise

    def _update_layered_window(self, x: int, y: int) -> None:
        """Update layered window position and content"""
        try:
            dest = wintypes.POINT(x, y)
            size = wintypes.SIZE(self.width, self.height)
            src_pos = wintypes.POINT(0, 0)
            blend = BLENDFUNCTION(win32con.AC_SRC_OVER, 0, 255, win32con.AC_SRC_ALPHA)

            # Reset last error so we can report meaningful failures from UpdateLayeredWindow.
            kernel32.SetLastError(0)

            # Call UpdateLayeredWindow directly via ctypes for consistent struct marshaling.
            result = user32.UpdateLayeredWindow(
                self.hwnd,
                self.hdc_screen,
                ctypes.byref(dest),
                ctypes.byref(size),
                self.hdc_mem,
                ctypes.byref(src_pos),
                0,
                ctypes.byref(blend),
                win32con.ULW_ALPHA
            )

            if not result:
                last_error = kernel32.GetLastError()
                if last_error:
                    try:
                        error_message = win32api.FormatMessage(last_error).strip()
                    except Exception:
                        error_message = f"FormatMessage failed for code {last_error}"
                else:
                    error_message = "Unknown error"
                self.logger.error(
                    "UpdateLayeredWindow failed: code=%s message=%s", last_error, error_message
                )
                raise RuntimeError("UpdateLayeredWindow failed")

            self.logger.debug(f"Layered window updated at ({x}, {y})")

        except Exception as e:
            self.logger.error(f"Error updating layered window: {e}")
            raise

    def move(self, x: int, y: int) -> None:
        """Move the layered window to new position"""
        if not self.hwnd or not self.is_visible:
            return

        try:
            self._update_layered_window(x, y)
            # Ensure the position is applied at the OS level as well
            try:
                import win32con
                win32gui.SetWindowPos(
                    self.hwnd,
                    win32con.HWND_TOPMOST,
                    x, y, 0, 0,
                    win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
                )
            except Exception:
                pass
        except Exception as e:
            self.logger.error(f"Error moving overlay: {e}")

    def show(self) -> None:
        """Show the layered window"""
        if self.hwnd and not self.is_visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            self.is_visible = True
            self.logger.debug("LayeredOverlay shown")

    def hide(self) -> None:
        """Hide the layered window"""
        if self.hwnd and self.is_visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
            self.is_visible = False
            self.logger.debug("LayeredOverlay hidden")

    def destroy(self) -> None:
        """Destroy the layered window and cleanup resources"""
        try:
            if self.hwnd:
                if self.is_visible:
                    win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                win32gui.DestroyWindow(self.hwnd)
                self.hwnd = None
                self.is_visible = False

            self._cleanup_gdi_resources()
            self.logger.debug("LayeredOverlay destroyed")

        except Exception as e:
            self.logger.error(f"Error destroying overlay: {e}")

    def _cleanup_gdi_resources(self) -> None:
        """Clean up GDI resources"""
        try:
            if self.old_bitmap and self.hdc_mem:
                win32gui.SelectObject(self.hdc_mem, self.old_bitmap)
                self.old_bitmap = None

            if self.hbitmap:
                win32gui.DeleteObject(self.hbitmap)
                self.hbitmap = None

            if self.hdc_mem:
                win32gui.DeleteDC(self.hdc_mem)
                self.hdc_mem = None

            if self.hdc_screen:
                win32gui.ReleaseDC(0, self.hdc_screen)
                self.hdc_screen = None

        except Exception as e:
            self.logger.error(f"Error cleaning up GDI resources: {e}")

    def _window_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure for handling mouse events"""
        try:
            if msg == win32con.WM_NCHITTEST:
                # Let Windows handle dragging - entire window is draggable
                return win32con.HTCAPTION

            elif msg == win32con.WM_ENTERSIZEMOVE:
                # Optional safety hook for future diagnostics
                self.in_move_loop = True
                return 0

            elif msg == win32con.WM_EXITSIZEMOVE:
                # Optional safety hook for future diagnostics
                self.in_move_loop = False
                return 0

            elif msg in (win32con.WM_NCLBUTTONDBLCLK, win32con.WM_LBUTTONDBLCLK):
                # Double-click to restore (callback queues work back to Tk thread).
                self.logger.info("Double-click detected - triggering restore")
                try:
                    self.on_restore()
                except Exception as e:
                    self.logger.error(f"Error triggering restore: {e}")
                return 0

            elif msg == win32con.WM_DESTROY:
                self.is_visible = False
                return 0

        except Exception as e:
            self.logger.error(f"Error in window proc: {e}")

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    # Manual drag logic removed - Windows handles dragging via HTCAPTION
    # Restore is now only triggered by double-click

    def __del__(self):
        """Destructor - ensure cleanup"""
        try:
            self.destroy()
        except Exception:
            pass
